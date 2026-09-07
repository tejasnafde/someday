"""Reverse geocoding: coordinates -> city name, via OSM Nominatim.

Volume here is tiny (a handful of moment posts a day), well inside Nominatim's
usage policy. The request goes through safe_client so the SSRF posture matches
every other outbound call, and the UA identifies us per their policy.
"""

from urllib.parse import urlencode

from app_util.log_util import errorlogger, infologger
from common_helper.url_util import safe_client
from config.settings import settings

TIMEOUT = 5.0
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SomedayBot/1.0; +https://someday.app)"}

# Most-specific first. Nominatim puts the human-scale name in different keys
# depending on the place type.
CITY_KEYS = ("city", "town", "village", "suburb", "county", "state_district", "state")


def pick_city(address: dict) -> str | None:
    """The human-scale place name from a Nominatim address object."""
    for key in CITY_KEYS:
        if address.get(key):
            return str(address[key])[:40]
    return None


def reverse_geocode_city(lat: float, lng: float) -> str | None:
    """Best-effort city name for coordinates. None on any failure."""
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0):
        return None
    params = urlencode({"lat": f"{lat:.5f}", "lon": f"{lng:.5f}", "format": "jsonv2", "zoom": 10})
    url = f"{settings.NOMINATIM_URL}/reverse?{params}"
    try:
        with safe_client(timeout=TIMEOUT, headers=HEADERS) as client:
            resp = client.get(url)
        resp.raise_for_status()
        city = pick_city(resp.json().get("address", {}))
        if city:
            infologger.info(f"geo_util.reverse_geocode_city | ({lat:.3f},{lng:.3f}) -> {city!r}")
        else:
            infologger.warning(f"geo_util.reverse_geocode_city | no city key in address | ({lat:.3f},{lng:.3f})")
        return city
    except Exception as exc:
        errorlogger.error(f"geo_util.reverse_geocode_city | failed | {exc}")
        return None
