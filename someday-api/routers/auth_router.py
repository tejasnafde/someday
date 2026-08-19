from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from pydantic import BaseModel, field_validator

from app_util.log_util import errorlogger, infologger
from common_helper.auth_helper import jwt_required
from common_helper.decorators import log_timing
from common_helper.discord_alert import alert as discord_alert
from common_helper.product_analytics import track_product_event
from common_helper.response_helper import create_response
from handler.auth_handler import AuthHandler
from schemas.auth_schema import MeOut, UserResponse, WebviewSessionOut

router = APIRouter()
handler = AuthHandler()


class ClientErrorRequest(BaseModel):
    context: str  # e.g. "google_oauth_exchange"
    message: str  # error message from the SDK
    detail: Optional[str] = None  # extra info (url shape, etc.)


class PushTokenRequest(BaseModel):
    token: Optional[str] = None


class UpdateMeRequest(BaseModel):
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None

    @field_validator("display_name")
    def name_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("display_name cannot be blank")
        return v


@router.post("/client-error")
@log_timing("POST /auth/client-error")
async def client_error(request: ClientErrorRequest):
    """
    Receives client-side auth errors (e.g. exchangeCodeForSession failures) that
    never reach the backend otherwise, and fires a Discord alert so they're visible.
    No JWT required - the user can't be authenticated when sign-in fails.
    """
    errorlogger.error(
        f"CLIENT_AUTH_ERROR | context={request.context} | {request.message}"
        + (f" | {request.detail}" if request.detail else "")
    )
    discord_alert(400, "CLIENT", f"/auth/{request.context}", request.message)
    return create_response(200, "logged")


@router.post("/verify", response_model=UserResponse)
@log_timing("POST /auth/verify")
async def verify(background_tasks: BackgroundTasks, current_user: dict = Depends(jwt_required)):
    """
    Called once after Supabase magic-link auth completes on the client.
    Upserts the user row and returns the profile.
    The JWT is already validated by jwt_required - payload contains sub + email.
    """
    infologger.info(f"POST /auth/verify | user_id={current_user['sub']}")
    status, result = handler.verify(current_user["sub"], current_user.get("email", ""))
    if status == 200:
        background_tasks.add_task(track_product_event, "auth_account_verified", "auth")
    return create_response(status, result)


@router.get("/me", response_model=MeOut)
@log_timing("GET /auth/me")
async def get_me(current_user: dict = Depends(jwt_required)):
    """Return current user profile + their circles."""
    infologger.info(f"GET /auth/me | user_id={current_user['sub']}")
    status, result = handler.get_me(current_user["sub"])
    return create_response(status, result)


@router.patch("/me", response_model=UserResponse)
@log_timing("PATCH /auth/me")
async def update_me(request: UpdateMeRequest, current_user: dict = Depends(jwt_required)):
    """Update display name / avatar."""
    infologger.info(
        f"PATCH /auth/me | user_id={current_user['sub']} payload={request.model_dump(exclude_none=True)}"
    )
    status, result = handler.update_me(
        current_user["sub"], request.display_name, request.avatar_url
    )
    return create_response(status, result)


@router.post("/me/avatar", response_model=UserResponse)
@log_timing("POST /auth/me/avatar")
async def upload_avatar(file: UploadFile = File(...), current_user: dict = Depends(jwt_required)):
    """Upload a profile photo (client sends a pre-resized webp/jpeg/png ≤2MB)."""
    infologger.info(
        f"POST /auth/me/avatar | user_id={current_user['sub']} type={file.content_type}"
    )
    content = await file.read()
    status, result = handler.upload_avatar(current_user["sub"], content, file.content_type or "")
    return create_response(status, result)


@router.patch("/me/push-token")
@log_timing("PATCH /auth/me/push-token")
async def set_push_token(request: PushTokenRequest, current_user: dict = Depends(jwt_required)):
    """Register or clear the Expo push token for this device."""
    infologger.info(
        f"PATCH /auth/me/push-token | user_id={current_user['sub']} set={'yes' if request.token else 'no'}"
    )
    status, result = handler.set_push_token(current_user["sub"], request.token)
    return create_response(status, result)


@router.post("/webview-session", response_model=WebviewSessionOut)
@log_timing("POST /auth/webview-session")
async def webview_session(current_user: dict = Depends(jwt_required)):
    """Mint an independent session for the mobile WebView (separate refresh-token family)."""
    infologger.info(f"POST /auth/webview-session | user_id={current_user['sub']}")
    status, result = handler.webview_session(current_user.get("email", ""))
    return create_response(status, result)
