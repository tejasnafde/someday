"""Supabase JWT verification - RS256 via JWKS."""

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient, PyJWTError

from app_util.log_util import errorlogger, infologger
from config.settings import settings

security = HTTPBearer()

# Caches JWKS at import time, thread-safe. Re-fetches if kid is unknown.
jwks_client = PyJWKClient(
    f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json",
    cache_jwk_set=True,
    lifespan=3600,  # re-fetch public keys at most once per hour
)


def verify_supabase_jwt(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    token = credentials.credentials
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
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
    """Dependency alias - use this in router Depends() calls."""
    return payload
