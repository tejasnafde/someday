"""
Someday API — FastAPI entry point.

Startup order:
    1. Logging configured (log_util imported by handlers before this runs)
    2. DB engine initialised (pool created once)
    3. Middleware registered (request/response logging)
    4. Routers mounted

Every request logs: METHOD PATH user=<id>
Every response logs: STATUS duration_ms
"""

import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app_util.db_util import DBUtil
from app_util.log_util import infologger, errorlogger
from config.settings import settings
from routers import (
    auth_router,
    circles_router,
    intents_router,
    payoff_router,
    unfurl_router,
)

app = FastAPI(
    title="Someday API",
    version="0.1.0",
    docs_url="/docs" if settings.APP_ENV == "dev" else None,
    redoc_url=None,
)

# ── CORS ─────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request / response logging middleware ─────────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    t0 = time.perf_counter()
    # Extract user id from auth header if present (best-effort, no validation here)
    auth = request.headers.get("authorization", "")
    user_hint = "anonymous"
    if auth.startswith("Bearer "):
        # Log only first 8 chars of token as a trace hint — never log full token
        user_hint = f"token:{auth[7:15]}…"

    infologger.info(
        f"REQUEST | {request.method} {request.url.path} | user={user_hint}"
    )

    try:
        response = await call_next(request)
    except Exception as exc:
        ms = (time.perf_counter() - t0) * 1000
        errorlogger.error(f"REQUEST_UNHANDLED | {request.url.path} | {ms:.1f}ms | {exc}", exc_info=True)
        raise

    ms = (time.perf_counter() - t0) * 1000
    infologger.info(f"RESPONSE | {response.status_code} | {ms:.1f}ms")
    return response

# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup() -> None:
    DBUtil.init_engine()
    infologger.info(f"STARTUP | Someday API v0.1.0 | env={settings.APP_ENV}")

# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok", "env": settings.APP_ENV}

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(auth_router.router,    prefix="/auth",    tags=["auth"])
app.include_router(circles_router.router, prefix="/circles", tags=["circles"])
app.include_router(intents_router.router, prefix="",         tags=["intents"])
app.include_router(payoff_router.router,  prefix="",         tags=["payoff"])
app.include_router(unfurl_router.router,  prefix="/unfurl",  tags=["unfurl"])
