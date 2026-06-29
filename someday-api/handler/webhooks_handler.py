"""EAS build webhook → GitHub release. Native releases become: eas build → done."""

import hashlib
import hmac
import re
import tempfile

import httpx

from app_util.log_util import errorlogger, infologger
from common_helper.decorators import log_timing
from common_helper.notify import Notify
from config.settings import settings

def verify_signature(body: bytes, signature: str) -> bool:
    expected = "sha1=" + hmac.new(
        settings.EAS_WEBHOOK_SECRET.encode(), body, hashlib.sha1
    ).hexdigest()
    return hmac.compare_digest(expected, signature or "")


def github(method: str, url: str, upload=False, **kwargs) -> httpx.Response:
    headers = kwargs.pop("headers", {})
    headers.update({
        "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    })
    # ponytail: upload timeout is long because APKs are ~80 MB
    timeout = httpx.Timeout(connect=30, read=120, write=600, pool=30) if upload else 120
    return httpx.request(method, url, headers=headers, timeout=timeout, **kwargs)


def release_exists(version: str) -> bool:
    r = github("GET", f"https://api.github.com/repos/{settings.GITHUB_REPO}/releases/tags/v{version}")
    return r.status_code == 200


def upload_and_notify(version: str, apk_url: str, release_id: int) -> None:
    """Download the APK from apk_url, upload it to the GitHub release, then push + Discord."""
    with tempfile.NamedTemporaryFile(suffix=".apk") as tmp:
        with httpx.stream("GET", apk_url, timeout=300, follow_redirects=True) as resp:
            resp.raise_for_status()
            for chunk in resp.iter_bytes(1024 * 1024):
                tmp.write(chunk)
        tmp.flush()
        infologger.info(f"webhooks.upload_and_notify | artifact downloaded | {tmp.tell()} bytes")
        tmp.seek(0)
        up = github(
            "POST",
            f"https://uploads.github.com/repos/{settings.GITHUB_REPO}/releases/{release_id}/assets?name=someday.apk",
            headers={"Content-Type": "application/vnd.android.package-archive"},
            content=tmp.read(),
            upload=True,
        )
        up.raise_for_status()
    infologger.info(f"webhooks.upload_and_notify | v{version} published with someday.apk")
    Notify().update_released(version)
    if settings.DISCORD_WEBHOOK_URL:
        try:
            r = httpx.post(settings.DISCORD_WEBHOOK_URL, timeout=5, json={
                "username": "Someday",
                "content": f"🚀 **Someday v{version}** released - APK live on GitHub, update banner active for all users.",
            })
            if r.status_code >= 400:
                errorlogger.error(f"webhooks.upload_and_notify | discord notify failed | status={r.status_code} body={r.text[:200]}")
            else:
                infologger.info(f"webhooks.upload_and_notify | discord notified | v{version}")
        except Exception as exc:
            errorlogger.error(f"webhooks.upload_and_notify | discord notify failed | {exc}")


def publish_release(version: str, apk_url: str, build_id: str) -> None:
    """Create the GitHub release then call upload_and_notify."""
    infologger.info(f"webhooks.publish_release | v{version} | build={build_id}")
    if release_exists(version):
        infologger.warning(f"webhooks.publish_release | v{version} already exists - skipping")
        return
    try:
        rel = github("POST", f"https://api.github.com/repos/{settings.GITHUB_REPO}/releases", json={
            "tag_name": f"v{version}",
            "name": f"Someday v{version}",
            "body": (
                f"Automated release from EAS build `{build_id}`.\n"
                f"apk_url: {apk_url}\n\n"
                "Installed apps offer this version via the in-app update banner."
            ),
        })
        rel.raise_for_status()
        upload_and_notify(version, apk_url, rel.json()["id"])
    except Exception as exc:
        errorlogger.error(f"webhooks.publish_release | failed | v{version} | {exc}", exc_info=True)
        raise


def recover_incomplete_releases() -> None:
    """On startup, complete any release that was created but never had its APK uploaded.

    This handles the race where an EAS webhook fires mid-deployment: the background task
    creates the GitHub release but the old instance is killed before the APK upload finishes.
    Recovery finds releases with no someday.apk asset and an 'apk_url: ...' line in the body.
    """
    try:
        r = github("GET", f"https://api.github.com/repos/{settings.GITHUB_REPO}/releases?per_page=5")
        r.raise_for_status()
        for rel in r.json():
            if any(a["name"] == "someday.apk" for a in rel.get("assets", [])):
                continue
            match = re.search(r"apk_url: (https://\S+)", rel.get("body", ""))
            if not match:
                infologger.warning(
                    f"webhooks.recover | {rel['tag_name']} has no APK and no recoverable apk_url - skipping"
                )
                continue
            version = rel["tag_name"].lstrip("v")
            infologger.warning(f"webhooks.recover | v{version} incomplete - resuming upload")
            upload_and_notify(version, match.group(1), rel["id"])
    except Exception as exc:
        errorlogger.error(f"webhooks.recover | {exc}", exc_info=True)


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
