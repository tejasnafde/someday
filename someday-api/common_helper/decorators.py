"""Decorators - apply to every router endpoint and handler method."""

import asyncio
import functools
import time

from app_util.log_util import errorlogger, infologger


def log_timing(name: str):
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                t0 = time.perf_counter()
                infologger.info(f"[{name}] START")
                try:
                    result = await func(*args, **kwargs)
                    ms = (time.perf_counter() - t0) * 1000
                    infologger.info(f"[{name}] END | {ms:.1f}ms")
                    return result
                except Exception as exc:
                    ms = (time.perf_counter() - t0) * 1000
                    errorlogger.error(f"[{name}] ERROR | {ms:.1f}ms | {exc}", exc_info=True)
                    raise
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                t0 = time.perf_counter()
                infologger.info(f"[{name}] START")
                try:
                    result = func(*args, **kwargs)
                    ms = (time.perf_counter() - t0) * 1000
                    infologger.info(f"[{name}] END | {ms:.1f}ms")
                    return result
                except Exception as exc:
                    ms = (time.perf_counter() - t0) * 1000
                    errorlogger.error(f"[{name}] ERROR | {ms:.1f}ms | {exc}", exc_info=True)
                    raise
            return sync_wrapper
    return decorator
