"""One-off backfill: re-host expired link-preview images into Supabase Storage.

Existing intents stored the raw og:image URL. Many of those are signed CDN URLs
(Instagram/FB scontent, S3 presigned, etc.) that have since expired, showing as
broken JPEGs. This downloads each one — or re-unfurls the source page when the
direct image is dead — and re-hosts it permanently in the `previews` bucket.

Run against an environment explicitly (INFO logging shows per-row progress):

    cd someday-api
    APP_ENV=production LOG_LEVEL=INFO python scripts/backfill_preview_images.py
    APP_ENV=production LOG_LEVEL=INFO python scripts/backfill_preview_images.py --dry-run

Safe to re-run: already-rehosted images are skipped, and re-hosting is
idempotent (storage path is a hash of the source URL).
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_util.db_util import DBUtil  # noqa: E402
from app_util.log_util import infologger  # noqa: E402
from config.settings import settings  # noqa: E402
from common_helper.storage_helper import is_rehosted, rehost_remote_image  # noqa: E402
from handler.unfurl_handler import fetch_link_meta  # noqa: E402
from modules.intents import intents_queries as q  # noqa: E402


def coerce_meta(value) -> dict | None:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="report only; write nothing")
    args = parser.parse_args()

    db = DBUtil()
    rows = db.execute_query_with_value(
        q.SELECT_INTENTS_WITH_REMOTE_PREVIEW,
        {"rehosted_prefix": f"{settings.SUPABASE_URL}/storage/%"},
    )
    infologger.info(
        f"backfill_preview_images | env={settings.APP_ENV} candidates={len(rows)} dry_run={args.dry_run}"
    )

    fixed = recovered = skipped = failed = 0
    for r in rows:
        intent_id = r["id"]
        meta = coerce_meta(r.get("link_meta"))
        image = meta.get("image") if meta else None
        if not meta or not image or is_rehosted(image):
            skipped += 1
            continue

        new_url = rehost_remote_image(image)
        source = "direct"
        if not new_url and r.get("url"):
            # Direct image is dead — re-unfurl the source page for a fresh og:image
            # (fetch_link_meta with rehost=True re-hosts it for us).
            fresh = fetch_link_meta(r["url"], rehost=True)
            if fresh and is_rehosted(fresh.get("image") or ""):
                meta, new_url, source = fresh, fresh["image"], "reunfurl"

        if not new_url:
            failed += 1
            infologger.warning(f"backfill | FAILED intent_id={intent_id} | {image[:100]}")
            continue

        meta["image"] = new_url
        if not args.dry_run:
            db.execute_query_with_value_returning(
                q.UPDATE_INTENT_META, {"intent_id": intent_id, "link_meta": json.dumps(meta)}
            )
        if source == "direct":
            fixed += 1
        else:
            recovered += 1
        infologger.info(f"backfill | OK[{source}] intent_id={intent_id} -> {new_url[:100]}")

    infologger.info(
        f"backfill_preview_images | done fixed={fixed} recovered={recovered} "
        f"skipped={skipped} failed={failed}"
    )


if __name__ == "__main__":
    main()
