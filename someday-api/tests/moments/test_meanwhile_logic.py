import random
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from modules.moments.moments_helper import (
    WAKING_END_HOUR,
    WAKING_START_HOUR,
    can_post,
    draw_moment_dates,
    ping_time_utc,
    posts_visible,
    safe_zone,
    week_bounds,
)


def test_week_bounds_monday_to_sunday():
    start, end = week_bounds(date(2026, 9, 9))  # a Wednesday
    assert start == date(2026, 9, 7)
    assert end == date(2026, 9, 13)
    assert start.weekday() == 0
    assert end.weekday() == 6


def test_draw_fills_to_cadence_from_remaining_days():
    rng = random.Random(42)
    today = date(2026, 9, 9)  # Wednesday
    drawn = draw_moment_dates([], 3, today, rng)
    assert len(drawn) == 3
    assert all(today <= d <= date(2026, 9, 13) for d in drawn)
    assert len(set(drawn)) == 3


def test_draw_counts_existing_moments():
    rng = random.Random(1)
    today = date(2026, 9, 9)
    existing = [date(2026, 9, 7), date(2026, 9, 8)]  # already fired this week
    drawn = draw_moment_dates(existing, 3, today, rng)
    assert len(drawn) == 1
    assert drawn[0] >= today


def test_draw_never_exceeds_cadence():
    rng = random.Random(2)
    today = date(2026, 9, 9)
    existing = [date(2026, 9, 7), date(2026, 9, 8), date(2026, 9, 9)]
    assert draw_moment_dates(existing, 3, today, rng) == []
    assert draw_moment_dates(existing, 2, today, rng) == []


def test_draw_caps_at_remaining_days():
    rng = random.Random(3)
    today = date(2026, 9, 13)  # Sunday - one candidate day left
    drawn = draw_moment_dates([], 3, today, rng)
    assert drawn == [date(2026, 9, 13)]


def test_draw_ignores_other_weeks():
    rng = random.Random(4)
    today = date(2026, 9, 9)
    existing = [date(2026, 9, 2)]  # last week - must not count
    drawn = draw_moment_dates(existing, 1, today, rng)
    assert len(drawn) == 1


def test_ping_time_is_inside_local_waking_window():
    for tz_name in ["Asia/Kolkata", "America/Toronto", "Europe/Berlin", "Australia/Sydney"]:
        for seed in range(20):
            rng = random.Random(seed)
            utc = ping_time_utc(date(2026, 9, 9), tz_name, rng)
            assert utc.tzinfo == timezone.utc
            local = utc.astimezone(ZoneInfo(tz_name))
            assert local.date() == date(2026, 9, 9)
            assert WAKING_START_HOUR <= local.hour < WAKING_END_HOUR


def test_ping_time_half_hour_zone():
    # Asia/Kolkata is UTC+5:30 - conversion must not land outside the window.
    rng = random.Random(7)
    utc = ping_time_utc(date(2026, 9, 9), "Asia/Kolkata", rng)
    local = utc.astimezone(ZoneInfo("Asia/Kolkata"))
    assert WAKING_START_HOUR <= local.hour < WAKING_END_HOUR


def test_safe_zone_falls_back_to_utc():
    assert str(safe_zone("Not/AZone")) == "UTC"
    assert str(safe_zone(None)) == "UTC"
    assert str(safe_zone("Asia/Kolkata")) == "Asia/Kolkata"


def test_posts_visible_after_posting():
    now = datetime(2026, 9, 9, 12, 0, tzinfo=timezone.utc)
    assert posts_visible(True, date(2026, 9, 9), "Asia/Kolkata", now)


def test_posts_hidden_same_day_without_posting():
    now = datetime(2026, 9, 9, 12, 0, tzinfo=timezone.utc)
    assert not posts_visible(False, date(2026, 9, 9), "Asia/Kolkata", now)


def test_posts_reveal_after_viewer_local_midnight():
    # 19:00 UTC on the 9th is already 00:30 on the 10th in Kolkata.
    now = datetime(2026, 9, 9, 19, 0, tzinfo=timezone.utc)
    assert posts_visible(False, date(2026, 9, 9), "Asia/Kolkata", now)
    # Same instant in Toronto is still the 9th - stays hidden there.
    assert not posts_visible(False, date(2026, 9, 9), "America/Toronto", now)


def test_can_post_today_and_grace_day():
    now = datetime(2026, 9, 9, 12, 0, tzinfo=timezone.utc)
    assert can_post(date(2026, 9, 9), "UTC", now)
    assert can_post(date(2026, 9, 8), "UTC", now)      # grace day
    assert not can_post(date(2026, 9, 7), "UTC", now)  # too old
    assert not can_post(date(2026, 9, 10), "UTC", now)  # future


def test_can_post_uses_poster_timezone():
    # 19:00 UTC on the 9th: Kolkata is already on the 10th, so the 9th is
    # their grace day and the 8th has closed.
    now = datetime(2026, 9, 9, 19, 0, tzinfo=timezone.utc)
    assert can_post(date(2026, 9, 9), "Asia/Kolkata", now)
    assert not can_post(date(2026, 9, 8), "Asia/Kolkata", now)
    # Toronto is still on the 9th, so the 8th is still open there.
    assert can_post(date(2026, 9, 8), "America/Toronto", now)
