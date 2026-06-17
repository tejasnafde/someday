"""EAS build webhook → GitHub release. Native releases become: eas build → done."""

import hashlib
import hmac
import tempfile

import httpx

from app_util.log_util import errorlogger, infologger
from common_helper.decorators import log_timing
from config.settings import settings

REPO = "tejasnafde/someday"


def verify_signature(body: bytes, signature: str) -> bool:
    expected = "sha1=" + hmac.new(
        settings.EAS_WEBHOOK_SECRET.encode(), body, hashlib.sha1
    ).hexdigest()
    return hmac.compare_digest(expected, signature or "")


def github(method: str, url: str, **kwargs) -> httpx.Response:
    headers = kwargs.pop("headers", {})
    headers.update({
        "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    })
    return httpx.request(method, url, headers=headers, timeout=120, **kwargs)


def release_exists(version: str) -> bool:
    r = github("GET", f"https://api.github.com/repos/{REPO}/releases/tags/v{version}")
    return r.status_code == 200


def publish_release(version: str, apk_url: str, build_id: str) -> None:
    """Download the APK artifact and publish it as GitHub release v{version}."""
    infologger.info(f"webhooks.publish_release | v{version} | build={build_id}")
    if release_exists(version):
        infologger.warning(f"webhooks.publish_release | v{version} already exists — skipping")
        return
    try:
        with tempfile.NamedTemporaryFile(suffix=".apk") as tmp:
            with httpx.stream("GET", apk_url, timeout=300, follow_redirects=True) as resp:
                resp.raise_for_status()
                for chunk in resp.iter_bytes(1024 * 1024):
                    tmp.write(chunk)
            tmp.flush()
            size = tmp.tell()
            infologger.info(f"webhooks.publish_release | artifact downloaded | {size} bytes")

            rel = github("POST", f"https://api.github.com/repos/{REPO}/releases", json={
                "tag_name": f"v{version}",
                "name": f"Someday v{version}",
                "body": f"Automated release from EAS build `{build_id}`.\n\n"
                        "Installed apps offer this version via the in-app update banner.",
            })
            rel.raise_for_status()
            release_id = rel.json()["id"]

            tmp.seek(0)
            up = github(
                "POST",
                f"https://uploads.github.com/repos/{REPO}/releases/{release_id}/assets?name=someday.apk",
                headers={"Content-Type": "application/vnd.android.package-archive"},
                content=tmp.read(),
            )
            up.raise_for_status()
        infologger.info(f"webhooks.publish_release | v{version} published with someday.apk")
        from common_helper.notify import Notify
        Notify().update_released(version)
    except Exception as exc:
        errorlogger.error(f"webhooks.publish_release | failed | v{version} | {exc}", exc_info=True)
        raise


class WebhooksHandler:

    @log_timing("webhooks_handler.eas_build")
    def eas_build(self, payload: dict) -> tuple[int, dict | str]:
        status = payload.get("status")
        platform = payload.get("platform")
        version = (payload.get("metadata") or {}).get("appVersion")
        apk_url = (payload.get("artifacts") or {}).get("buildUrl")
        build_id = payload.get("id", "?")
        infologger.info(
            f"WebhooksHandler.eas_build | build={build_id} status={status} "
            f"platform={platform} version={version}"
        )
        if status != "finished" or platform != "android":
            return 200, {"action": "ignored", "reason": f"{platform}/{status}"}
        if not version or not apk_url:
            infologger.warning("WebhooksHandler.eas_build | missing version or artifact")
            return 200, {"action": "ignored", "reason": "missing version/artifact"}
        return 200, {"action": "publish", "version": version, "apk_url": apk_url, "build_id": build_id}
