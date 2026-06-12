from typing import Optional

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, field_validator

from app_util.log_util import infologger
from common_helper.auth_helper import jwt_required
from common_helper.decorators import log_timing
from common_helper.response_helper import create_response
from handler.auth_handler import AuthHandler

router = APIRouter()
handler = AuthHandler()


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


@router.post("/verify")
@log_timing("POST /auth/verify")
async def verify(current_user: dict = Depends(jwt_required)):
    """
    Called once after Supabase magic-link auth completes on the client.
    Upserts the user row and returns the profile.
    The JWT is already validated by jwt_required — payload contains sub + email.
    """
    infologger.info(f"POST /auth/verify | user_id={current_user['sub']}")
    status, result = handler.verify(current_user["sub"], current_user.get("email", ""))
    return create_response(status, result)


@router.get("/me")
@log_timing("GET /auth/me")
async def get_me(current_user: dict = Depends(jwt_required)):
    """Return current user profile + their circles."""
    infologger.info(f"GET /auth/me | user_id={current_user['sub']}")
    status, result = handler.get_me(current_user["sub"])
    return create_response(status, result)


@router.patch("/me")
@log_timing("PATCH /auth/me")
async def update_me(request: UpdateMeRequest, current_user: dict = Depends(jwt_required)):
    """Update display name / avatar."""
    infologger.info(f"PATCH /auth/me | user_id={current_user['sub']} payload={request.model_dump(exclude_none=True)}")
    status, result = handler.update_me(current_user["sub"], request.display_name, request.avatar_url)
    return create_response(status, result)


@router.post("/me/avatar")
@log_timing("POST /auth/me/avatar")
async def upload_avatar(file: UploadFile = File(...), current_user: dict = Depends(jwt_required)):
    """Upload a profile photo (client sends a pre-resized webp/jpeg/png ≤2MB)."""
    infologger.info(f"POST /auth/me/avatar | user_id={current_user['sub']} type={file.content_type}")
    content = await file.read()
    status, result = handler.upload_avatar(current_user["sub"], content, file.content_type or "")
    return create_response(status, result)


@router.post("/webview-session")
@log_timing("POST /auth/webview-session")
async def webview_session(current_user: dict = Depends(jwt_required)):
    """Mint an independent session for the mobile WebView (separate refresh-token family)."""
    infologger.info(f"POST /auth/webview-session | user_id={current_user['sub']}")
    status, result = handler.webview_session(current_user.get("email", ""))
    return create_response(status, result)
