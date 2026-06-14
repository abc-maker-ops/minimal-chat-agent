# -*- coding: utf-8 -*-
"""Chat Completions 调用：全局限频 + 429/5xx 指数退避重试。"""
from __future__ import annotations

import os
import threading
import time
from typing import Any

from openai import APIStatusError, RateLimitError

_lock = threading.Lock()
_last_call_monotonic: float = 0.0


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _retry_after_seconds(exc: RateLimitError | APIStatusError) -> float | None:
    resp = getattr(exc, "response", None)
    if resp is None:
        return None
    header = resp.headers.get("retry-after") or resp.headers.get("Retry-After")
    if not header:
        return None
    try:
        return max(0.0, float(header))
    except ValueError:
        return None


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, RateLimitError):
        return True
    if isinstance(exc, APIStatusError) and exc.status_code in {429, 500, 502, 503, 504}:
        return True
    return False


def _throttle_before_call() -> None:
    """两次 API 调用之间的最小间隔，避免 burst 触发平台频控。"""
    global _last_call_monotonic
    min_interval = _env_float("API_MIN_INTERVAL_SEC", 1.5)
    if min_interval <= 0:
        return
    with _lock:
        now = time.monotonic()
        wait = min_interval - (now - _last_call_monotonic)
        if wait > 0:
            time.sleep(wait)
        _last_call_monotonic = time.monotonic()


def create_chat_completion(client: Any, **body: Any) -> Any:
    """带全局限频与退避的 chat.completions.create 包装。"""
    max_retries = _env_int("API_RETRY_MAX", 6)
    base_delay = _env_float("API_RETRY_BASE_SEC", 2.0)
    max_delay = _env_float("API_RETRY_MAX_SEC", 60.0)

    attempt = 0
    while True:
        _throttle_before_call()
        try:
            return client.chat.completions.create(**body)
        except BaseException as exc:
            if not _is_retryable(exc) or attempt >= max_retries:
                if isinstance(exc, RateLimitError):
                    raise RuntimeError(
                        "智谱 API 429 限流：已自动重试仍失败。"
                        "请稍后再试，或增大 API_MIN_INTERVAL_SEC（如 2～3）、"
                        "降低 CONSISTENCY_SAMPLES，并检查账户配额。"
                    ) from exc
                raise
            retry_after = None
            if isinstance(exc, (RateLimitError, APIStatusError)):
                retry_after = _retry_after_seconds(exc)
            delay = retry_after if retry_after is not None else min(
                max_delay, base_delay * (2**attempt)
            )
            attempt += 1
            time.sleep(delay)
