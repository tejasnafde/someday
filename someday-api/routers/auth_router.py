from fastapi import APIRouter, Depends

from app_util.log_util import infologger
from common_helper.auth_helper import jwt_required
from common_helper.decorators import log_timing
from common_helper.response_helper import create_response
from handler.auth_handler import AuthHandler

router = APIRouter()
_handler = AuthHandler()


@router.post("/verify")
@log_timing("POST /auth/verify")
async def verify(current_user: dict = Depends(jwt_required)):
    """
    Called once after Supabase magic-link auth completes on the client.
    Upserts the user row and returns the profile.
    The JWT is already validated by jwt_required — payload contains sub + email.
    """
    infologger.info(f"POST /auth/verify | user_id={current_user['sub']}")
    status, result = _handler.verify(current_user["sub"], current_user.get("email", ""))
    return create_response(status, result)


@router.get("/me")
@log_timing("GET /auth/me")
async def get_me(current_user: dict = Depends(jwt_required)):
    """Return current user profile + their circles."""
    infologger.info(f"GET /auth/me | user_id={current_user['sub']}")
    status, result = _handler.get_me(current_user["sub"])
    return create_response(status, result)
