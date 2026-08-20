from io import BytesIO

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


def test_github_transport_preserves_content_length_for_stream(monkeypatch):
    apk = b"streamed apk"
    captured = {}

    def fake_request(method, url, *, headers, content, **kwargs):
        request = httpx.Request(method, url, headers=headers, content=content)
        captured["headers"] = request.headers
        captured["body"] = request.read()
        return response(201, url, json={"state": "uploaded"})

    monkeypatch.setattr(webhooks_handler.httpx, "request", fake_request)

    webhooks_handler.github(
        "POST",
        "https://uploads.github.test/assets",
        headers={
            "Content-Type": "application/vnd.android.package-archive",
            "Content-Length": str(len(apk)),
        },
        content=webhooks_handler.apk_chunks(BytesIO(apk)),
        upload=True,
    )

    assert captured["headers"]["content-length"] == str(len(apk))
    assert "transfer-encoding" not in captured["headers"]
    assert captured["body"] == apk


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
            assert kwargs["headers"]["Content-Length"] == str(len(apk))
            assert b"".join(kwargs["content"]) == apk
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


def test_malformed_preflight_response_does_not_block_upload(monkeypatch):
    apk = b"upload despite malformed preflight"
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
            return response(200, url, content=b"<html>bad gateway</html>")
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


def test_malformed_race_verification_preserves_upload_diagnostic(monkeypatch):
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
            if asset_checks == 1:
                return response(200, url, json=[])
            return response(200, url, content=b"<html>bad gateway</html>")
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
        {"message": "bad\u2028forged", "errors": ["already_exists"]},
    ],
)
def test_upload_diagnostics_handle_unexpected_json_shapes(payload):
    upload_response = response(422, "https://uploads.github.test/assets", json=payload)

    with pytest.raises(RuntimeError, match=r"status=422") as raised:
        webhooks_handler.raise_upload_error(upload_response)

    assert "\r" not in str(raised.value)
    assert "\u2028" not in str(raised.value)


def test_non_json_upload_diagnostic_is_bounded_and_secret_safe():
    upload_response = response(
        502,
        "https://uploads.github.test/assets",
        content=b"upstream failed Authorization: Bearer super-secret-token",
    )

    with pytest.raises(RuntimeError, match="upstream failed") as raised:
        webhooks_handler.raise_upload_error(upload_response)

    assert "super-secret-token" not in str(raised.value)


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


def test_recovery_continues_after_one_release_fails(monkeypatch):
    releases_url = "https://api.github.test/releases"
    releases = [
        {
            "id": 1,
            "tag_name": "v1.15.0",
            "body": "apk_url: https://expo.test/one.apk",
            "assets": [],
        },
        {
            "id": 2,
            "tag_name": "v1.16.0",
            "body": "apk_url: https://expo.test/two.apk",
            "assets": [],
        },
    ]
    attempted = []

    monkeypatch.setattr(
        webhooks_handler,
        "github",
        lambda *args, **kwargs: response(200, releases_url, json=releases),
    )

    def fake_upload(version, apk_url, release_id, *, send_notifications=True):
        attempted.append((release_id, send_notifications))
        if release_id == 1:
            raise RuntimeError("stuck asset")

    monkeypatch.setattr(webhooks_handler, "upload_and_notify", fake_upload)

    webhooks_handler.recover_incomplete_releases()

    assert attempted == [(1, False), (2, False)]


def test_recovery_ignores_malformed_entries_and_continues(monkeypatch):
    releases_url = "https://api.github.test/releases"
    releases = [
        "junk",
        {
            "id": 99,
            "tag_name": "v1.16.0",
            "body": "apk_url: https://expo.test/app.apk",
            "assets": [],
        },
    ]
    attempted = []

    monkeypatch.setattr(
        webhooks_handler,
        "github",
        lambda *args, **kwargs: response(200, releases_url, json=releases),
    )
    monkeypatch.setattr(
        webhooks_handler,
        "upload_and_notify",
        lambda version, apk_url, release_id, **kwargs: attempted.append(release_id),
    )

    webhooks_handler.recover_incomplete_releases()

    assert attempted == [99]


def test_recovery_does_not_retry_name_occupying_incomplete_asset(monkeypatch):
    releases_url = "https://api.github.test/releases"
    releases = [
        {
            "id": 1,
            "tag_name": "v1.16.0",
            "body": "apk_url: https://expo.test/app.apk",
            "assets": [{"name": "someday.apk", "state": "new"}],
        }
    ]

    monkeypatch.setattr(
        webhooks_handler,
        "github",
        lambda *args, **kwargs: response(200, releases_url, json=releases),
    )
    monkeypatch.setattr(
        webhooks_handler,
        "upload_and_notify",
        lambda *args, **kwargs: pytest.fail("stuck named assets require manual intervention"),
    )

    webhooks_handler.recover_incomplete_releases()
