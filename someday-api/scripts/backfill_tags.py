"""One-off backfill: auto-tag every active intent that has no tags.

Almost all intents arrive via the mobile share sheet, which has no tag field,
so the library is largely untagged. This runs the same two-pass tagger used on
intent create (domain heuristics, then Vertex gemini flash lite against a
closed vocabulary) over every untagged intent.

Run against an environment explicitly (INFO logging shows per-row progress):

    cd someday-api
    APP_ENV=production LOG_LEVEL=INFO python scripts/backfill_tags.py --dry-run
    APP_ENV=production LOG_LEVEL=INFO python scripts/backfill_tags.py
    APP_ENV=production LOG_LEVEL=INFO python scripts/backfill_tags.py --limit 50

Safe to re-run: only intents with zero tags are selected, and the write is
guarded so a concurrent manual edit always wins. Requires ADC with access to
the Vertex project (gcloud auth application-default login), else the LLM pass
degrades to heuristics only.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_util.db_util import DBUtil  # noqa: E402
from app_util.log_util import infologger  # noqa: E402
from config.settings import settings  # noqa: E402
from modules.tagging import tagging_helper as h  # noqa: E402
from modules.tagging import tagging_queries as q  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="report only; write nothing")
    parser.add_argument("--limit", type=int, default=1000, help="max intents to process")
    args = parser.parse_args()

    db = DBUtil()
    rows = db.execute_query_with_value(q.SELECT_UNTAGGED_INTENTS, {"limit": args.limit})
    infologger.info(
        f"backfill_tags | env={settings.APP_ENV} model={settings.TAGGER_MODEL} "
        f"candidates={len(rows)} dry_run={args.dry_run}"
    )

    tagged = empty = 0
    for r in rows:
        # Dry run still calls the LLM (that is the point - see the tags it
        # would pick) but writes nothing.
        tags = h.auto_tag_intent(db, r["id"], dry_run=args.dry_run)
        if tags:
            tagged += 1
        else:
            empty += 1

    infologger.info(f"backfill_tags | done tagged={tagged} nothing_fit={empty}")


if __name__ == "__main__":
    main()
