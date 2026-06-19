"""Supabase Storage uploads via the service key — clients never touch storage directly."""

import hashlib

import httpx

from app_util.log_util import errorlogger, infologger
from common_helper.url_util import validate_url
from config.settings import settings

MAX_BYTES = 5 * 1024 * 1024
ALLOWED_TYPES = {"image/webp", "image/jpeg", "image/png"}
# Source CDNs label JPEGs inconsistently; normalise to a type the bucket accepts.
CONTENT_TYPE_ALIASES = {"image/jpg": "image/jpeg", "image/pjpeg": "image/jpeg"}
REHOST_FETCH_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SomedayBot/1.0; +https://someday.app)"
}


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


def is_rehosted(image_url: str | None) -> bool:
    """True if this URL already points at our own Supabase Storage (permanent)."""
    return bool(image_url) and image_url.startswith(f"{settings.SUPABASE_URL}/storage/")


def rehost_remote_image(remote_url: str, bucket: str = "previews") -> str | None:
    """Download a remote image (e.g. an og:image) and re-host it in Supabase
    Storage so it survives the source CDN's signed-URL expiry. Returns the
    permanent public URL, or None so the caller can fall back to the original.

    The storage path is derived from a hash of the source URL, so re-hosting
    the same image twice is idempotent (and upserts in place)."""
    if is_rehosted(remote_url):
        return remote_url  # already ours — nothing to do
    try:
        validate_url(remote_url)
    except ValueError as exc:
        infologger.warning(f"storage.rehost | blocked URL | {exc} | {remote_url[:120]}")
        return None
    try:
        resp = httpx.get(
            remote_url, headers=REHOST_FETCH_HEADERS, timeout=15, follow_redirects=True
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        # Source already dead/expired — caller keeps the original URL.
        infologger.warning(f"storage.rehost | fetch failed | {remote_url[:120]} | {exc}")
        return None

    content_type = resp.headers.get("content-type", "").split(";")[0].strip().lower()
    content_type = CONTENT_TYPE_ALIASES.get(content_type, content_type)
    ext = {"image/webp": "webp", "image/jpeg": "jpg", "image/png": "png"}.get(content_type)
    if not ext:
        infologger.warning(f"storage.rehost | unsupported type={content_type!r} | {remote_url[:120]}")
        return None

    digest = hashlib.sha256(remote_url.encode("utf-8")).hexdigest()[:32]
    return upload_public_image(bucket, f"{digest}.{ext}", resp.content, content_type)
