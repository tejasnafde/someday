import httpx
import pytest

from handler import webhooks_handler


class ResponseContext:
    def __init__(self, response: httpx.Response):
        self.response = response

    def __enter__(self):
        return self.response

    def __exit__(self, exc_type, exc, traceback):
        return False


def response(status_code: int, url: str, **kwargs) -> httpx.Response:
    return httpx.Response(status_code, request=httpx.Request("GET", url), **kwargs)


def test_duplicate_upload_race_does_not_repeat_release_notifications(monkeypatch):
    apk = b"verified apk bytes"
    asset_checks = 0
    notified = []

    monkeypatch.setattr(
        webhooks_handler.httpx,
        "stream",
        lambda *args, **kwargs: ResponseContext(
            response(200, "https://expo.test/app.apk", content=apk)
        ),
    )

    def fake_github(method, url, **kwargs):
        nonlocal asset_checks
        if method == "GET" and "/assets" in url:
            asset_checks += 1
            assets = [] if asset_checks == 1 else [
                {
                    "name": "someday.apk",
                    "size": len(apk),
                    "state": "uploaded",
                }
            ]
            return response(200, url, json=assets)
        if method == "POST" and "uploads.github.com" in url:
            return response(
                422,
                url,
                json={"message": "Validation Failed", "errors": [{"code": "already_exists"}]},
            )
        raise AssertionError(f"Unexpected GitHub request: {method} {url}")

    class FakeNotify:
        def update_released(self, version):
            notified.append(version)

    monkeypatch.setattr(webhooks_handler, "github", fake_github)
    monkeypatch.setattr(webhooks_handler, "Notify", FakeNotify)
    monkeypatch.setattr(webhooks_handler.settings, "DISCORD_WEBHOOK_URL", "")

    webhooks_handler.upload_and_notify("1.16.0", "https://expo.test/app.apk", 123)

    assert asset_checks == 2
    assert notified == []


def test_matching_uploaded_asset_skips_upload_and_release_notifications(monkeypatch):
    apk = b"already uploaded apk"
    notified = []

    monkeypatch.setattr(
        webhooks_handler.httpx,
        "stream",
        lambda *args, **kwargs: ResponseContext(
            response(200, "https://expo.test/app.apk", content=apk)
        ),
    )

    def fake_github(method, url, **kwargs):
        assert method == "GET"
        assert "/assets" in url
        return response(
            200,
            url,
            json=[{"name": "someday.apk", "size": len(apk), "state": "uploaded"}],
        )

    class FakeNotify:
        def update_released(self, version):
            notified.append(version)

    monkeypatch.setattr(webhooks_handler, "github", fake_github)
    monkeypatch.setattr(webhooks_handler, "Notify", FakeNotify)
    monkeypatch.setattr(webhooks_handler.settings, "DISCORD_WEBHOOK_URL", "")

    webhooks_handler.upload_and_notify("1.16.0", "https://expo.test/app.apk", 123)

    assert notified == []


def test_successful_upload_completes_release_notifications(monkeypatch):
    apk = b"newly uploaded apk"
    notified = []

    monkeypatch.setattr(
        webhooks_handler.httpx,
        "stream",
        lambda *args, **kwargs: ResponseContext(
            response(200, "https://expo.test/app.apk", content=apk)
        ),
    )

    def fake_github(method, url, **kwargs):
        if method == "GET" and url.endswith("/assets?per_page=100"):
            return response(200, url, json=[])
        if method == "POST" and "uploads.github.com" in url:
            return response(201, url, json={"name": "someday.apk", "state": "uploaded"})
        raise AssertionError(f"Unexpected GitHub request: {method} {url}")

    class FakeNotify:
        def update_released(self, version):
            notified.append(version)

    monkeypatch.setattr(webhooks_handler, "github", fake_github)
    monkeypatch.setattr(webhooks_handler, "Notify", FakeNotify)
    monkeypatch.setattr(webhooks_handler.settings, "DISCORD_WEBHOOK_URL", "")

    webhooks_handler.upload_and_notify("1.16.0", "https://expo.test/app.apk", 123)

    assert notified == ["1.16.0"]


def test_transient_preflight_failure_does_not_block_upload(monkeypatch):
    apk = b"upload despite preflight failure"
    notified = []

    monkeypatch.setattr(
        webhooks_handler.httpx,
        "stream",
        lambda *args, **kwargs: ResponseContext(
            response(200, "https://expo.test/app.apk", content=apk)
        ),
    )

    def fake_github(method, url, **kwargs):
        if method == "GET" and url.endswith("/assets?per_page=100"):
            return response(503, url, json={"message": "temporarily unavailable"})
        if method == "POST" and "uploads.github.com" in url:
            return response(201, url, json={"name": "someday.apk", "state": "uploaded"})
        raise AssertionError(f"Unexpected GitHub request: {method} {url}")

    class FakeNotify:
        def update_released(self, version):
            notified.append(version)

    monkeypatch.setattr(webhooks_handler, "github", fake_github)
    monkeypatch.setattr(webhooks_handler, "Notify", FakeNotify)
    monkeypatch.setattr(webhooks_handler.settings, "DISCORD_WEBHOOK_URL", "")

    webhooks_handler.upload_and_notify("1.16.0", "https://expo.test/app.apk", 123)

    assert notified == ["1.16.0"]


def test_duplicate_name_with_wrong_size_remains_a_diagnostic_failure(monkeypatch):
    apk = b"new apk bytes"
    notified = []

    monkeypatch.setattr(
        webhooks_handler.httpx,
        "stream",
        lambda *args, **kwargs: ResponseContext(
            response(200, "https://expo.test/app.apk", content=apk)
        ),
    )

    def fake_github(method, url, **kwargs):
        if method == "GET" and "/assets" in url:
            return response(
                200,
                url,
                json=[
                    {
                        "name": "someday.apk",
                        "size": len(apk) + 1,
                        "state": "uploaded",
                    }
                ],
            )
        if method == "POST" and "uploads.github.com" in url:
            return response(
                422,
                url,
                json={"message": "Validation Failed", "errors": [{"code": "already_exists"}]},
            )
        raise AssertionError(f"Unexpected GitHub request: {method} {url}")

    class FakeNotify:
        def update_released(self, version):
            notified.append(version)

    monkeypatch.setattr(webhooks_handler, "github", fake_github)
    monkeypatch.setattr(webhooks_handler, "Notify", FakeNotify)
    monkeypatch.setattr(webhooks_handler.settings, "DISCORD_WEBHOOK_URL", "")

    with pytest.raises(RuntimeError, match=r"status=422.*already_exists"):
        webhooks_handler.upload_and_notify("1.16.0", "https://expo.test/app.apk", 123)

    assert notified == []


def test_failed_race_verification_preserves_upload_diagnostic(monkeypatch):
    apk = b"apk bytes"
    asset_checks = 0

    monkeypatch.setattr(
        webhooks_handler.httpx,
        "stream",
        lambda *args, **kwargs: ResponseContext(
            response(200, "https://expo.test/app.apk", content=apk)
        ),
    )

    def fake_github(method, url, **kwargs):
        nonlocal asset_checks
        if method == "GET" and "/assets" in url:
            asset_checks += 1
            status = 200 if asset_checks == 1 else 503
            return response(status, url, json=[] if status == 200 else {"message": "unavailable"})
        if method == "POST" and "uploads.github.com" in url:
            return response(
                422,
                url,
                json={"message": "Validation Failed", "errors": [{"code": "already_exists"}]},
            )
        raise AssertionError(f"Unexpected GitHub request: {method} {url}")

    monkeypatch.setattr(webhooks_handler, "github", fake_github)
    monkeypatch.setattr(webhooks_handler.settings, "DISCORD_WEBHOOK_URL", "")

    with pytest.raises(RuntimeError, match=r"status=422.*already_exists"):
        webhooks_handler.upload_and_notify("1.16.0", "https://expo.test/app.apk", 123)


@pytest.mark.parametrize(
    "payload",
    [
        ["bad gateway"],
        {"message": "Validation Failed", "errors": None},
        {"message": "bad\rforged", "errors": ["already_exists"]},
    ],
)
def test_upload_diagnostics_handle_unexpected_json_shapes(payload):
    upload_response = response(422, "https://uploads.github.test/assets", json=payload)

    with pytest.raises(RuntimeError, match=r"status=422") as raised:
        webhooks_handler.raise_upload_error(upload_response)

    assert "\r" not in str(raised.value)


def test_empty_artifact_is_rejected_before_github_calls(monkeypatch):
    monkeypatch.setattr(
        webhooks_handler.httpx,
        "stream",
        lambda *args, **kwargs: ResponseContext(
            response(200, "https://expo.test/app.apk", content=b"")
        ),
    )
    monkeypatch.setattr(
        webhooks_handler,
        "github",
        lambda *args, **kwargs: pytest.fail("GitHub must not receive an empty APK"),
    )

    with pytest.raises(RuntimeError, match="empty APK"):
        webhooks_handler.upload_and_notify("1.16.0", "https://expo.test/app.apk", 123)
