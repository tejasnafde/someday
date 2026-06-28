import base64
import json

from fastapi import APIRouter, BackgroundTasks, Query, Request
from fastapi.responses import JSONResponse

from app_util.log_util import infologger
from common_helper.decorators import log_timing
from common_helper.discord_alert import send_build_alert
from common_helper.response_helper import create_response
from config.settings import settings
from handler.webhooks_handler import WebhooksHandler, publish_release, verify_signature

FAILED_BUILD_STATUSES = {"FAILURE", "INTERNAL_ERROR", "TIMEOUT", "EXPIRED", "CANCELLED"}

router = APIRouter()
handler = WebhooksHandler()


@router.post("/eas-build")
@log_timing("POST /webhooks/eas-build")
async def eas_build(request: Request, background: BackgroundTasks):
    """EAS build notification — HMAC-verified, release published in the background
    so the webhook responds before EAS's delivery timeout."""
    body = await request.body()
    if not verify_signature(body, request.headers.get("expo-signature", "")):
        infologger.warning("POST /webhooks/eas-build | bad signature")
        return JSONResponse(status_code=401, content={"message": "bad signature"})

    payload = json.loads(body)
    status, result = handler.eas_build(payload)
    if isinstance(result, dict) and result.get("action") == "publish":
        background.add_task(
            publish_release, result["version"], result["apk_url"], result["build_id"]
        )
        return create_response(200, {"queued": f"v{result['version']}"})
    return create_response(status, result)


@router.post("/cloud-build")
@log_timing("POST /webhooks/cloud-build")
async def cloud_build(request: Request, background: BackgroundTasks, token: str = Query(default="")):
    """Pub/Sub push from the `cloud-builds` topic. Alerts Discord when a someday-api deploy
    fails, so a broken build can't silently sit behind the previous (stale) revision.
    Always returns 200 (except bad token) so Pub/Sub doesn't retry healthy/ignored messages."""
    # ponytail: shared-token auth via query param; swap to Pub/Sub OIDC verification if the URL ever leaks
    if not settings.CLOUDBUILD_ALERT_TOKEN or token != settings.CLOUDBUILD_ALERT_TOKEN:
        infologger.warning("POST /webhooks/cloud-build | bad token")
        return JSONResponse(status_code=401, content={"message": "bad token"})

    envelope = await request.json()
    msg = envelope.get("message", {}) or {}
    status = (msg.get("attributes", {}) or {}).get("status", "")
    if status not in FAILED_BUILD_STATUSES:
        return create_response(200, {"ignored": status or "no-status"})

    raw = base64.b64decode(msg["data"]).decode() if msg.get("data") else "{}"
    if "someday-api" not in raw:  # the topic carries every build in the project
        return create_response(200, {"ignored": "other-build"})

    data = json.loads(raw)
    commit = (data.get("substitutions", {}) or {}).get("COMMIT_SHA", "")
    background.add_task(send_build_alert, data.get("id", ""), status, data.get("logUrl", ""), commit)
    infologger.warning(f"POST /webhooks/cloud-build | deploy {status} | build={data.get('id', '')}")
    return create_response(200, {"alerted": status})
