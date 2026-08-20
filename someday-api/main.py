"""Someday API - FastAPI entry point."""

import threading
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app_util.db_util import DBUtil
from app_util.log_util import errorlogger, infologger
from common_helper.error_alert import StructuredErrorAlertMiddleware
from config.settings import settings
from handler.webhooks_handler import recover_incomplete_releases
from routers import (
    auth_router,
    circles_router,
    intents_router,
    notifications_router,
    payoff_router,
    push_router,
    tour_router,
    unfurl_router,
    webhooks_router,
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
    infologger.info(f"REQUEST | {request.method} {request.url.path}")

    try:
        response = await call_next(request)
    except Exception as exc:
        ms = (time.perf_counter() - t0) * 1000
        errorlogger.error(f"REQUEST_UNHANDLED | {request.url.path} | {ms:.1f}ms | {exc}", exc_info=True)
        raise

    ms = (time.perf_counter() - t0) * 1000
    infologger.info(f"RESPONSE | {response.status_code} | {ms:.1f}ms")
    return response


app.add_middleware(StructuredErrorAlertMiddleware)

# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup() -> None:
    DBUtil.init_engine()
    infologger.info(f"STARTUP | Someday API v0.1.0 | env={settings.APP_ENV}")
    if settings.APP_ENV == "production":
        threading.Thread(target=recover_incomplete_releases, daemon=True).start()

# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/", tags=["meta"])
@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok", "env": settings.APP_ENV}

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(auth_router.router,          prefix="/auth",    tags=["auth"])
app.include_router(circles_router.router,       prefix="/circles", tags=["circles"])
app.include_router(intents_router.router,       prefix="",         tags=["intents"])
app.include_router(notifications_router.router, prefix="",         tags=["notifications"])
app.include_router(push_router.router,          prefix="",         tags=["push"])
app.include_router(payoff_router.router,        prefix="",         tags=["payoff"])
app.include_router(tour_router.router,          prefix="/tour",    tags=["tour"])
app.include_router(unfurl_router.router,        prefix="/unfurl",  tags=["unfurl"])
app.include_router(webhooks_router.router,      prefix="/webhooks", tags=["webhooks"])
