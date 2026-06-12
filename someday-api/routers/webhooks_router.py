import json

from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import JSONResponse

from app_util.log_util import infologger
from common_helper.decorators import log_timing
from common_helper.response_helper import create_response
from handler.webhooks_handler import WebhooksHandler, publish_release, verify_signature

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
