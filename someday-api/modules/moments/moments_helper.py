"""Meanwhile moments: scheduling, reveal rules, and posts.

Scheduling model:
- A cron tick (Cloud Scheduler -> /moments/tick) runs every few minutes.
- Once per ISO week per circle, the tick draws `moments_cadence` random days
  from the remaining days of the UTC week (today through Sunday).
- For each drawn day, every member gets a ping at a random minute inside
  their LOCAL waking window (09:00-21:59) on that date. Same calendar day
  for the circle, humane hour for each member.
- Due pings are sent as push notifications and marked sent. Everything is
  idempotent (unique indexes + ON CONFLICT DO NOTHING), so overlapping or
  replayed ticks are harmless.

Reveal rule:
- A viewer sees the posts of a moment once they have posted to it, or once
  the moment day is over in the viewer's own timezone. Until then they only
  see WHO has posted.
"""

import random
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app_util.log_util import errorlogger, infologger
from common_helper.push_helper import send_push
from modules.moments import moments_queries as q

WAKING_START_HOUR = 9    # never ping before 09:00 local
WAKING_END_HOUR = 22     # last ping minute is 21:59 local
LATE_GRACE_SECONDS = 60  # posts after ping_at + grace are labeled late
POST_MAX_AGE_DAYS = 1    # can post to today's or yesterday's moment (local)


def as_date(value) -> date:
    """DBUtil serializes rows through pandas, so date columns arrive as strings
    (sometimes full timestamps). Accept date | str defensively."""
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return date.fromisoformat(str(value)[:10])


def safe_zone(tz_name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(tz_name or "UTC")
    except Exception:
        return ZoneInfo("UTC")


def week_bounds(today: date) -> tuple[date, date]:
    """Monday..Sunday of the UTC week containing `today`."""
    start = today - timedelta(days=today.weekday())
    return start, start + timedelta(days=6)


def draw_moment_dates(existing: list[date], cadence: int, today: date, rng: random.Random) -> list[date]:
    """Pick dates for the rest of this week so the total reaches `cadence`.

    Only today and future days are candidates - a mid-week cadence change never
    backfills past days. At most one moment per day (unique index enforces it
    too). Returns the NEW dates to insert.
    """
    week_start, week_end = week_bounds(today)
    existing_in_week = {d for d in existing if week_start <= d <= week_end}
    needed = cadence - len(existing_in_week)
    if needed <= 0:
        return []
    candidates = []
    d = max(today, week_start)
    while d <= week_end:
        if d not in existing_in_week:
            candidates.append(d)
        d += timedelta(days=1)
    return sorted(rng.sample(candidates, min(needed, len(candidates))))


def ping_time_utc(moment_date: date, tz_name: str | None, rng: random.Random) -> datetime:
    """A random waking-hours minute on `moment_date` in the member's zone, as UTC."""
    zone = safe_zone(tz_name)
    minute_of_window = rng.randrange((WAKING_END_HOUR - WAKING_START_HOUR) * 60)
    local = datetime.combine(
        moment_date,
        time(WAKING_START_HOUR + minute_of_window // 60, minute_of_window % 60),
        tzinfo=zone,
    )
    return local.astimezone(timezone.utc)


def posts_visible(viewer_posted: bool, moment_date: date, viewer_tz: str | None, now_utc: datetime) -> bool:
    """Post-to-see during the day; everything reveals after the viewer's local midnight."""
    if viewer_posted:
        return True
    viewer_today = now_utc.astimezone(safe_zone(viewer_tz)).date()
    return moment_date < viewer_today


def can_post(moment_date: date, poster_tz: str | None, now_utc: datetime) -> bool:
    """Posting allowed on the moment day and one grace day after, poster-local."""
    poster_today = now_utc.astimezone(safe_zone(poster_tz)).date()
    return timedelta(0) <= (poster_today - moment_date) <= timedelta(days=POST_MAX_AGE_DAYS)


def draw_week_schedules(db, rng: random.Random | None = None, now_utc: datetime | None = None) -> int:
    """Ensure every opted-in circle has its moments drawn for this week."""
    rng = rng or random.Random()
    now_utc = now_utc or datetime.now(timezone.utc)
    today = now_utc.date()
    created = 0
    for circle in db.execute_query_with_value(q.LIST_CIRCLES_WITH_CADENCE, {}):
        week_start, week_end = week_bounds(today)
        rows = db.execute_query_with_value(
            q.LIST_WEEK_MOMENT_DATES,
            {"circle_id": circle["id"], "week_start": str(week_start), "week_end": str(week_end)},
        )
        existing = [as_date(r["moment_date"]) for r in rows]
        for new_date in draw_moment_dates(existing, circle["moments_cadence"], today, rng):
            row = db.execute_query_with_value_returning(
                q.INSERT_MOMENT, {"circle_id": circle["id"], "moment_date": str(new_date)}
            )
            if row:
                created += 1
    if created:
        infologger.info(f"moments_helper.draw_week_schedules | created={created}")
    return created


def ensure_pings(db, rng: random.Random | None = None, now_utc: datetime | None = None) -> int:
    """Create missing pings for current and next-day moments (members can join late)."""
    rng = rng or random.Random()
    now_utc = now_utc or datetime.now(timezone.utc)
    today = now_utc.date()
    # Yesterday..a week ahead covers timezone skew on both sides.
    moments = db.execute_query_with_value(
        q.LIST_MOMENTS_NEEDING_PINGS,
        {"min_date": str(today - timedelta(days=1)), "max_date": str(today + timedelta(days=7))},
    )
    created = 0
    for m in moments:
        members = db.execute_query_with_value(q.LIST_MEMBER_TIMEZONES, {"circle_id": m["circle_id"]})
        pinged = {r["user_id"] for r in db.execute_query_with_value(
            q.LIST_MOMENT_PING_USER_IDS, {"moment_id": m["id"]}
        )}
        for member in members:
            if member["user_id"] in pinged:
                continue
            ping_at = ping_time_utc(as_date(m["moment_date"]), member["timezone"], rng)
            db.execute_query_with_value_without_output(
                q.INSERT_PING,
                {"moment_id": m["id"], "user_id": member["user_id"], "ping_at": ping_at.isoformat()},
            )
            created += 1
    if created:
        infologger.info(f"moments_helper.ensure_pings | created={created}")
    return created


def send_due_pings(db, notify) -> int:
    """Push every due unsent ping, then mark the batch sent."""
    due = db.execute_query_with_value(q.LIST_DUE_PINGS, {})
    if not due:
        return 0
    for ping in due:
        body = "Meanwhile - what are you doing right now?"
        path = f"/moments/{ping['moment_id']}"
        try:
            if ping.get("push_token"):
                send_push(db, [ping["push_token"]], ping["circle_name"], body, path)
            notify.send_web_push([str(ping["user_id"])], ping["circle_name"], body, path)
        except Exception as exc:
            errorlogger.error(f"moments_helper.send_due_pings | push failed | ping={ping['id']} | {exc}")
    db.execute_query_with_value_without_output(
        q.MARK_PINGS_SENT, {"ping_ids": [str(p["id"]) for p in due]}
    )
    infologger.info(f"moments_helper.send_due_pings | sent={len(due)}")
    return len(due)


def moment_with_posts(db, moment_id: str, viewer_id: str, now_utc: datetime | None = None) -> dict | None:
    """One moment with its posts, reveal rule applied for this viewer."""
    now_utc = now_utc or datetime.now(timezone.utc)
    rows = db.execute_query_with_value(q.GET_MOMENT_FOR_MEMBER, {"moment_id": moment_id, "user_id": viewer_id})
    if not rows:
        return None
    moment = dict(rows[0])
    posts = db.execute_query_with_value(q.LIST_POSTS_FOR_MOMENTS, {"moment_ids": [moment_id]})
    viewer_rows = db.execute_query_with_value(q.GET_USER_TIMEZONE, {"user_id": viewer_id})
    viewer_tz = viewer_rows[0]["timezone"] if viewer_rows else "UTC"
    viewer_posted = any(str(p["user_id"]) == str(viewer_id) for p in posts)
    revealed = posts_visible(viewer_posted, as_date(moment["moment_date"]), viewer_tz, now_utc)
    moment["revealed"] = revealed
    moment["my_post"] = next((p for p in posts if str(p["user_id"]) == str(viewer_id)), None)
    if revealed:
        moment["posts"] = posts
    else:
        # Proof of life only: who posted, nothing else.
        moment["posts"] = [
            {"id": p["id"], "user_id": p["user_id"], "display_name": p["display_name"],
             "avatar_url": p["avatar_url"], "tz": p["tz"], "created_at": p["created_at"],
             "photo_url": None, "caption": None, "late": p["late"]}
            for p in posts
        ]
    return moment


def list_moments(db, circle_id: str, viewer_id: str, cursor: str | None, limit: int,
                 now_utc: datetime | None = None) -> dict:
    """Paginated timeline of a circle's moments, reveal rule applied per moment."""
    now_utc = now_utc or datetime.now(timezone.utc)
    moments = db.execute_query_with_value(
        q.LIST_MOMENTS_FOR_CIRCLE,
        {"circle_id": circle_id, "user_id": viewer_id, "cursor": cursor, "limit": limit},
    )
    if not moments:
        return {"items": [], "next_cursor": None}
    posts = db.execute_query_with_value(
        q.LIST_POSTS_FOR_MOMENTS, {"moment_ids": [str(m["id"]) for m in moments]}
    )
    viewer_rows = db.execute_query_with_value(q.GET_USER_TIMEZONE, {"user_id": viewer_id})
    viewer_tz = viewer_rows[0]["timezone"] if viewer_rows else "UTC"
    by_moment: dict[str, list[dict]] = {}
    for p in posts:
        by_moment.setdefault(str(p["moment_id"]), []).append(p)
    items = []
    for m in moments:
        entry = dict(m)
        m_posts = by_moment.get(str(m["id"]), [])
        viewer_posted = any(str(p["user_id"]) == str(viewer_id) for p in m_posts)
        revealed = posts_visible(viewer_posted, as_date(entry["moment_date"]), viewer_tz, now_utc)
        entry["revealed"] = revealed
        if revealed:
            entry["posts"] = m_posts
        else:
            entry["posts"] = [
                {"id": p["id"], "user_id": p["user_id"], "display_name": p["display_name"],
                 "avatar_url": p["avatar_url"], "tz": p["tz"], "created_at": p["created_at"],
                 "photo_url": None, "caption": None, "late": p["late"]}
                for p in m_posts
            ]
        items.append(entry)
    next_cursor = moments[-1]["moment_date"] if len(moments) == limit else None
    return {"items": items, "next_cursor": next_cursor}
