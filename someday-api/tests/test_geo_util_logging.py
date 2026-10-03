"""The city lookup must never log coordinates (the privacy policy says they are not kept)."""

import httpx

from common_helper import geo_util

LAT, LNG = 12.97123, 77.59456


def run(monkeypatch, handler):
    lines = []
    for logger in (geo_util.infologger, geo_util.errorlogger):
        for level in ("info", "warning", "error"):
            monkeypatch.setattr(logger, level, lambda msg, *a, **k: lines.append(str(msg)))
    monkeypatch.setattr(
        geo_util, "safe_client", lambda **kw: httpx.Client(transport=httpx.MockTransport(handler), **kw)
    )
    city = geo_util.reverse_geocode_city(LAT, LNG)
    return city, lines


def assert_no_coordinates(lines):
    assert lines
    for line in lines:
        assert "12.97" not in line and "77.59" not in line, line


def test_success_logs_city_only(monkeypatch):
    city, lines = run(monkeypatch, lambda req: httpx.Response(200, json={"address": {"city": "Bengaluru"}}))
    assert city == "Bengaluru"
    assert_no_coordinates(lines)


def test_no_city_logs_no_coordinates(monkeypatch):
    city, lines = run(monkeypatch, lambda req: httpx.Response(200, json={"address": {}}))
    assert city is None
    assert_no_coordinates(lines)


def test_http_error_logs_no_coordinates(monkeypatch):
    # httpx puts the request URL, coordinates included, in the exception text.
    city, lines = run(monkeypatch, lambda req: httpx.Response(503))
    assert city is None
    assert_no_coordinates(lines)
