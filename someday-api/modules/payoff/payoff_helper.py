import random

from app_util.log_util import infologger, errorlogger
from modules.payoff import payoff_queries as q


def smart_pick(db, circle_id: str, user_id: str) -> dict | None:
    infologger.info(f"payoff_helper.smart_pick | circle_id={circle_id}")
    rows = db.execute_query_with_value(
        q.SMART_PICK, {"circle_id": circle_id, "user_id": user_id}
    )
    if not rows:
        infologger.warning(f"payoff_helper.smart_pick | empty shortlist or not a member | circle_id={circle_id}")
        return None

    row = rows[0]
    score       = float(row["score"] or 0)
    mutual_pts  = float(row["mutual_ratio"] or 0) * 40
    age_pts     = min(float(row["days_saved"] or 0) / 30, 1.0) * 20
    boost_pts   = float(row["has_boost"] or 0) * 40

    result = {
        "intent_id":  str(row["intent_id"]),
        "title":      row["title"],
        "link_meta":  row["link_meta"],
        "score":      round(score, 2),
        "breakdown": {
            "mutual_ratio":     round(float(row["mutual_ratio"] or 0), 3),
            "reaction_count":   int(row["reaction_count"] or 0),
            "days_saved":       round(float(row["days_saved"] or 0), 1),
            "has_boost":        bool(row["has_boost"]),
            "points": {
                "mutual":  round(mutual_pts, 1),
                "age":     round(age_pts, 1),
                "boost":   round(boost_pts, 1),
                "total":   round(score, 1),
            },
        },
    }
    infologger.info(
        f"payoff_helper.smart_pick | winner={result['intent_id']} "
        f"score={result['score']} | breakdown={result['breakdown']['points']}"
    )
    return result


def spin(db, circle_id: str, user_id: str) -> list[dict]:
    infologger.info(f"payoff_helper.spin | circle_id={circle_id}")
    rows = db.execute_query_with_value(q.SHORTLIST_FOR_SPIN, {"circle_id": circle_id, "user_id": user_id})
    if not rows:
        infologger.warning(f"payoff_helper.spin | empty shortlist or not a member | circle_id={circle_id}")
        return []

    # Shuffle server-side so all clients see the same order for a given spin request.
    # ponytail: default time-based seed is intentional — we want a different order each call, not reproducibility.
    random.shuffle(rows)
    infologger.info(f"payoff_helper.spin | {len(rows)} items shuffled")
    return [dict(r) for r in rows]
