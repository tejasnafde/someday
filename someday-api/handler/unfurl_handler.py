"""URL unfurl — fetch Open Graph metadata from any URL."""

from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx

from app_util.db_util import DBUtil
from app_util.log_util import infologger, errorlogger
from common_helper.decorators import log_timing

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


def fetch_link_meta(url: str) -> dict | None:
    """Returns {"title": ..., "image": ..., "site": ...} or None on failure."""
    infologger.info(f"unfurl.fetch_link_meta | url={url}")
    if urlparse(url).netloc.lower() in YOUTUBE_HOSTS:
        meta = fetch_youtube_meta(url)
        if meta:
            return meta
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
    return meta


class UnfurlHandler(DBUtil):

    @log_timing("unfurl_handler.unfurl")
    def unfurl(self, url: str) -> tuple[int, dict | str]:
        infologger.info(f"UnfurlHandler.unfurl | url={url}")
        meta = fetch_link_meta(url)
        if not meta:
            infologger.warning(f"UnfurlHandler.unfurl | fallback — no metadata | url={url}")
            return 200, {"title": None, "image": None, "site": None}
        return 200, meta
