"""
Supabase JWT verification — RS256 via JWKS.

Supabase now signs JWTs with RS256 using asymmetric keys.
The public keys are published at:
    {SUPABASE_URL}/auth/v1/.well-known/jwks.json

PyJWKClient fetches and caches the key set automatically,
re-fetching if the token's kid doesn't match any cached key.

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
from jwt import PyJWKClient, PyJWTError

from app_util.log_util import errorlogger, infologger
from config.settings import settings

_security = HTTPBearer()

# Initialised once at import time — caches JWKS, thread-safe.
_jwks_client = PyJWKClient(
    f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json",
    cache_jwk_set=True,
    lifespan=3600,  # re-fetch public keys at most once per hour
)


def verify_supabase_jwt(
    credentials: HTTPAuthorizationCredentials = Depends(_security),
) -> dict:
    token = credentials.credentials
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience="authenticated",
        )
        infologger.debug(f"JWT_VERIFIED | user_id={payload.get('sub')}")
        return payload
    except PyJWTError as exc:
        errorlogger.error(f"JWT_INVALID | {exc}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    except Exception as exc:
        # Network error fetching JWKS, malformed token, etc.
        errorlogger.error(f"JWT_ERROR | {exc}", exc_info=True)
        raise HTTPException(status_code=401, detail="Could not validate token")


def jwt_required(payload: dict = Depends(verify_supabase_jwt)) -> dict:
    """Dependency alias — use this in router Depends() calls."""
    return payload
