# -*- coding: utf-8 -*-
"""构建对接智谱的 LangChain ChatOpenAI。"""
from __future__ import annotations

import os

from langchain_openai import ChatOpenAI

from agent_session import (  # noqa: E402
    DEFAULT_ZHIPU_BASE_URL,
    DEFAULT_ZHIPU_MODEL,
    _get_api_key,
    _resolve_base_url,
    _resolve_timeout,
    load_config,
)


def build_chat_model() -> ChatOpenAI:
    cfg = load_config()
    kwargs: dict = {
        "model": cfg.model or DEFAULT_ZHIPU_MODEL,
        "api_key": _get_api_key(),
        "base_url": cfg.base_url or _resolve_base_url() or DEFAULT_ZHIPU_BASE_URL,
        "timeout": _resolve_timeout(),
    }
    if cfg.temperature is not None:
        kwargs["temperature"] = cfg.temperature
    if cfg.max_tokens is not None:
        kwargs["max_tokens"] = cfg.max_tokens
    raw = (os.getenv("API_MIN_INTERVAL_SEC") or "").strip()
    if raw:
        kwargs["max_retries"] = 3
    return ChatOpenAI(**kwargs)
