"""Supabase Storage uploads via the service key — clients never touch storage directly."""

import httpx

from app_util.log_util import errorlogger, infologger
from config.settings import settings

MAX_BYTES = 2 * 1024 * 1024
ALLOWED_TYPES = {"image/webp", "image/jpeg", "image/png"}


def upload_public_image(bucket: str, path: str, content: bytes, content_type: str) -> str | None:
    """Upload (upsert) an image and return its public URL, or None on failure."""
    if content_type not in ALLOWED_TYPES:
        infologger.warning(f"storage.upload | rejected content_type={content_type}")
        return None
    if len(content) > MAX_BYTES:
        infologger.warning(f"storage.upload | rejected size={len(content)}")
        return None
    try:
        resp = httpx.post(
            f"{settings.SUPABASE_URL}/storage/v1/object/{bucket}/{path}",
            headers={
                "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                "Content-Type": content_type,
                "x-upsert": "true",
            },
            content=content,
            timeout=30,
        )
        resp.raise_for_status()
        url = f"{settings.SUPABASE_URL}/storage/v1/object/public/{bucket}/{path}"
        infologger.info(f"storage.upload | ok | {bucket}/{path} ({len(content)} bytes)")
        return url
    except httpx.HTTPError as exc:
        errorlogger.error(f"storage.upload | failed | {bucket}/{path} | {exc}", exc_info=True)
        return None
