"""Supabase JWT verification - RS256 via JWKS."""

import hashlib
from datetime import UTC, datetime

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient, PyJWTError
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError

from app_util.log_util import errorlogger, infologger
from config.settings import settings

security = HTTPBearer()

# Caches JWKS at import time, thread-safe. Re-fetches if kid is unknown.
jwks_client = PyJWKClient(
    f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json",
    cache_jwk_set=True,
    lifespan=3600,  # re-fetch public keys at most once per hour
)


def token_diagnostics(token: str) -> dict:
    """Return correlatable JWT metadata without retaining the credential."""
    diagnostics = {
        "fingerprint": f"sha256:{hashlib.sha256(token.encode()).hexdigest()[:12]}",
        "token_length": len(token),
        "segments": len(token.split(".")),
    }
    try:
        payload = jwt.decode(
            token,
            options={"verify_signature": False, "verify_exp": False},
        )
    except (PyJWTError, TypeError, ValueError):
        return diagnostics

    try:
        expires_at = datetime.fromtimestamp(float(payload["exp"]), UTC)
    except (KeyError, TypeError, ValueError, OverflowError, OSError):
        pass
    else:
        diagnostics["expires_at"] = expires_at.isoformat()
    return diagnostics


def classify_jwt_error(exc: BaseException) -> str:
    if isinstance(exc, jwt.ExpiredSignatureError):
        return "expired"
    if isinstance(exc, jwt.InvalidSignatureError):
        return "invalid_signature"
    if isinstance(exc, jwt.DecodeError):
        return "malformed"
    if isinstance(exc, PyJWKClientConnectionError):
        return "jwks_unavailable"
    if isinstance(exc, PyJWKClientError):
        if "find a signing key" in str(exc).lower():
            return "unknown_signing_key"
        return "jwks_error"
    if isinstance(exc, jwt.InvalidAudienceError):
        return "invalid_audience"
    if isinstance(exc, jwt.InvalidIssuerError):
        return "invalid_issuer"
    if isinstance(exc, PyJWTError):
        return "invalid_token"
    return "validation_error"


def verify_supabase_jwt(
    request: Request,
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
        request.state.auth_alert = {
            "verification": "verified",
            **{
                key: payload[key]
                for key in ("sub", "email")
                if isinstance(payload.get(key), str) and payload[key]
            },
        }
        infologger.debug(f"JWT_VERIFIED | user_id={payload.get('sub')}")
        return payload
    except PyJWTError as exc:
        request.state.auth_alert = {
            "verification": "failed",
            **token_diagnostics(token),
            "reason": classify_jwt_error(exc),
        }
        errorlogger.error(f"JWT_INVALID | {exc}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    except Exception as exc:
        request.state.auth_alert = {
            "verification": "failed",
            **token_diagnostics(token),
            "reason": classify_jwt_error(exc),
        }
        # Network error fetching JWKS, malformed token, etc.
        errorlogger.error(f"JWT_ERROR | {exc}", exc_info=True)
        raise HTTPException(status_code=401, detail="Could not validate token")


def jwt_required(payload: dict = Depends(verify_supabase_jwt)) -> dict:
    """Dependency alias - use this in router Depends() calls."""
    return payload
