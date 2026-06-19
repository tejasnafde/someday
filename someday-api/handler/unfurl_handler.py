"""URL unfurl — fetch Open Graph metadata from any URL."""

from html.parser import HTMLParser
from urllib.parse import urlparse

import re

import httpx

from app_util.db_util import DBUtil
from app_util.log_util import infologger, errorlogger
from common_helper.decorators import log_timing
from common_helper.storage_helper import rehost_remote_image
from common_helper.url_util import validate_url

TIMEOUT = 8.0
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; SomedayBot/1.0; +https://someday.app)"
    )
}


class OGParser(HTMLParser):
    """Minimal parser — extracts <meta property="og:*"> and <title>."""

    def __init__(self):
        super().__init__()
        self.og: dict[str, str] = {}
        self.in_title = False
        self.title_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple]):
        if tag == "meta":
            a = dict(attrs)
            prop = a.get("property", "") or a.get("name", "")
            content = a.get("content", "")
            if prop.startswith("og:") and content:
                self.og[prop[3:]] = content
        elif tag == "title":
            self.in_title = True

    def handle_data(self, data: str):
        if self.in_title:
            self.title_text.append(data)

    def handle_endtag(self, tag: str):
        if tag == "title":
            self.in_title = False

    def fallback_title(self) -> str | None:
        return "".join(self.title_text).strip() or None


YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}
SHORTLINK_HOSTS = {"share.google", "maps.app.goo.gl", "goo.gl", "g.co"}


def resolve_shortlink(url: str) -> str:
    """Google's shorteners (share.google, goo.gl, g.co) redirect to the real
    destination — resolve before dispatching so maps/youtube handling applies."""
    if urlparse(url).netloc.lower() not in SHORTLINK_HOSTS:
        return url
    try:
        resp = httpx.get(url, timeout=TIMEOUT, follow_redirects=True, headers=HEADERS)
        final = str(resp.url)
        validate_url(final)  # guard against open-redirect to private IPs
        if final != url:
            infologger.info(f"unfurl.resolve_shortlink | {url} -> {final[:120]}")
        return final
    except ValueError as exc:
        infologger.warning(f"unfurl.resolve_shortlink | blocked redirect | {exc}")
        return url
    except Exception as exc:
        infologger.warning(f"unfurl.resolve_shortlink | failed | {exc}")
        return url
MAPS_HOSTS = {"maps.app.goo.gl", "goo.gl", "maps.google.com", "www.google.com", "google.com"}


def fetch_youtube_meta(url: str) -> dict | None:
    """YouTube serves stripped pages to datacenter IPs — oEmbed is reliable and keyless."""
    try:
        resp = httpx.get(
            "https://www.youtube.com/oembed",
            params={"url": url, "format": "json"},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        d = resp.json()
        meta = {"title": d.get("title"), "image": d.get("thumbnail_url"), "site": "YouTube"}
        infologger.info(f"unfurl.fetch_youtube_meta | success | title={meta['title']!r}")
        return meta
    except Exception as exc:
        infologger.warning(f"unfurl.fetch_youtube_meta | oEmbed failed, falling back to OG | {exc}")
        return None


def is_maps_url(url: str) -> bool:
    p = urlparse(url)
    host = p.netloc.lower()
    if host in {"maps.app.goo.gl", "maps.google.com"}:
        return True
    if host == "goo.gl" and p.path.startswith("/maps"):
        return True
    return host in {"www.google.com", "google.com"} and p.path.startswith("/maps")


def fetch_maps_meta(url: str) -> dict | None:
    """Google serves consent shells to datacenter IPs, but the place name is
    in the URL itself — resolve shortlinks, then parse /maps/place/<name>/ or ?q=."""
    from urllib.parse import parse_qs, unquote_plus

    try:
        p = urlparse(url)
        name = None
        m = re.search(r"/maps/place/([^/@?]+)", p.path)
        if m:
            name = unquote_plus(m.group(1))
        else:
            q = parse_qs(p.query).get("q", [None])[0]
            if q and not re.fullmatch(r"[-\d.,\s]+", q):  # skip bare coordinates
                name = unquote_plus(q)

        if not name:
            infologger.warning(f"unfurl.fetch_maps_meta | no place name in URL | {url[:120]}")
            return None

        meta = {"title": name, "image": None, "site": "Google Maps"}
        infologger.info(f"unfurl.fetch_maps_meta | success | title={name!r}")
        return meta
    except Exception as exc:
        infologger.warning(f"unfurl.fetch_maps_meta | failed, falling back to OG | {exc}")
        return None


def fetch_search_meta(url: str) -> dict | None:
    """share.google place links resolve to google.com/search?q=<place name>.
    From datacenter IPs Google interposes /sorry — but its continue= param
    still carries the original search URL, so parse the name out of that."""
    from urllib.parse import parse_qs, unquote, unquote_plus

    p = urlparse(url)
    if p.netloc.lower() not in {"www.google.com", "google.com"}:
        return None
    if p.path.startswith("/sorry"):
        cont = parse_qs(p.query).get("continue", [None])[0]
        return fetch_search_meta(unquote(cont)) if cont else None
    if p.path != "/search":
        return None
    q = parse_qs(p.query).get("q", [None])[0]
    if not q:
        return None
    meta = {"title": unquote_plus(q), "image": None, "site": "Google"}
    infologger.info(f"unfurl.fetch_search_meta | success | title={meta['title']!r}")
    return meta


def rehost_meta_image(meta: dict | None) -> dict | None:
    """Re-host meta['image'] into our own storage so the preview survives the
    source CDN's signed-URL expiry. Falls back to the original URL on failure."""
    if not meta or not meta.get("image"):
        return meta
    permanent = rehost_remote_image(meta["image"])
    if permanent:
        meta["image"] = permanent
    else:
        infologger.warning(f"unfurl.rehost_meta_image | kept original (rehost failed) | {meta['image'][:120]}")
    return meta


def fetch_link_meta(url: str, rehost: bool = True) -> dict | None:
    """Returns {"title": ..., "image": ..., "site": ...} or None on failure.

    When rehost is True (default — used when the result is persisted on an
    intent) the og:image is downloaded and re-hosted in Supabase Storage so it
    cannot expire. The standalone /unfurl preview passes rehost=False since that
    result is transient and should not create storage objects."""
    infologger.info(f"unfurl.fetch_link_meta | url={url} rehost={rehost}")
    try:
        validate_url(url)
    except ValueError as exc:
        infologger.warning(f"unfurl.fetch_link_meta | blocked URL | {exc} | url={url}")
        return None
    finish = rehost_meta_image if rehost else (lambda m: m)
    url = resolve_shortlink(url)
    if urlparse(url).netloc.lower() in YOUTUBE_HOSTS:
        meta = fetch_youtube_meta(url)
        if meta:
            return finish(meta)
    if is_maps_url(url):
        meta = fetch_maps_meta(url)
        if meta:
            return finish(meta)
    meta = fetch_search_meta(url)
    if meta:
        return finish(meta)
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        errorlogger.error(f"unfurl.fetch_link_meta | HTTP error | url={url} | {exc}")
        return None
    except Exception as exc:
        errorlogger.error(f"unfurl.fetch_link_meta | unexpected error | url={url} | {exc}")
        return None

    ct = resp.headers.get("content-type", "")
    if "html" not in ct:
        infologger.warning(f"unfurl.fetch_link_meta | non-HTML response | url={url} ct={ct}")
        return None

    parser = OGParser()
    try:
        parser.feed(resp.text)  # YouTube buries og: tags >600KB deep — parse everything
    except Exception as exc:
        errorlogger.error(f"unfurl.fetch_link_meta | parse error | {exc}")
        return None

    og = parser.og
    title = og.get("title") or parser.fallback_title()
    image = og.get("image")
    site  = og.get("site_name") or urlparse(url).netloc.replace("www.", "")

    if not title and not image:
        infologger.warning(f"unfurl.fetch_link_meta | no OG data found | url={url}")
        return None

    meta = {"title": title, "image": image, "site": site}
    infologger.info(f"unfurl.fetch_link_meta | success | title={title!r} site={site!r}")
    return finish(meta)


class UnfurlHandler(DBUtil):

    @log_timing("unfurl_handler.unfurl")
    def unfurl(self, url: str) -> tuple[int, dict | str]:
        infologger.info(f"UnfurlHandler.unfurl | url={url}")
        # Transient preview shown before saving — don't create storage objects.
        # The image is re-hosted later when the intent is actually persisted.
        meta = fetch_link_meta(url, rehost=False)
        if not meta:
            infologger.warning(f"UnfurlHandler.unfurl | fallback — no metadata | url={url}")
            return 200, {"title": None, "image": None, "site": None}
        return 200, meta
