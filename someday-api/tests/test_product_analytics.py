import json

from common_helper import product_analytics


def test_product_event_is_anonymous_and_schema_locked(monkeypatch):
    calls = []
    monkeypatch.setattr(product_analytics.settings, "APP_ENV", "production")
    monkeypatch.setattr(
        product_analytics.httpx,
        "post",
        lambda url, **kwargs: calls.append((url, kwargs)),
    )

    product_analytics.track_product_event("circle_created", "circles")

    assert len(calls) == 1
    url, kwargs = calls[0]
    assert url == "https://analytics.tn07.dev/v1/events"
    assert kwargs["headers"]["Origin"] == "https://someday.tn07.dev"
    payload = json.loads(kwargs["content"])
    assert payload == {
        "event": "circle_created",
        "event_version": 1,
        "product": "someday",
        "surface": "circles",
        "environment": "production",
        "authority": "server",
        "platform": "server",
        "properties": {},
    }
    assert not any(key in json.dumps(payload) for key in ("user_id", "circle_id", "email"))


def test_unknown_event_is_not_sent(monkeypatch):
    called = False

    def post(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(product_analytics.settings, "APP_ENV", "production")
    monkeypatch.setattr(product_analytics.httpx, "post", post)
    product_analytics.track_product_event("user_clicked_everything", "circles")
    assert called is False
