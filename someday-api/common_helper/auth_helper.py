"""
Supabase JWT verification.

Supabase signs JWTs with HS256 using SUPABASE_JWT_SECRET.
Decoded payload contains:
    sub   — user UUID (maps to users.id)
    email — user email
    role  — "authenticated" for valid sessions

Usage (in routers):
    from common_helper.auth_helper import jwt_required
    ...
    async def endpoint(current_user: dict = Depends(jwt_required)):
        user_id = current_user["sub"]
"""

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWTError

from app_util.log_util import errorlogger, infologger
from config.settings import settings

_security = HTTPBearer()


def verify_supabase_jwt(
    credentials: HTTPAuthorizationCredentials = Depends(_security),
) -> dict:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
        infologger.debug(f"JWT_VERIFIED | user_id={payload.get('sub')}")
        return payload
    except PyJWTError as exc:
        errorlogger.error(f"JWT_INVALID | {exc}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def jwt_required(payload: dict = Depends(verify_supabase_jwt)) -> dict:
    """Dependency alias — use this in router Depends() calls."""
    return payload
