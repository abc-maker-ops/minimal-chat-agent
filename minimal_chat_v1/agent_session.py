# -*- coding: utf-8 -*-
"""minimal_chat_v1 共享会话逻辑：CLI 与机制查看客户端共用。"""
from __future__ import annotations

import copy
import os
from dataclasses import dataclass, field

from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

_PKG_DIR = Path(__file__).resolve().parent
load_dotenv(_PKG_DIR / ".env", override=False)
load_dotenv(override=False)

# 系列默认走智谱 OpenAI 兼容网关；未配置时不要用 SDK 默认（api.openai.com，国内易超时）
DEFAULT_ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
DEFAULT_ZHIPU_MODEL = "glm-4.7-flash"
DEFAULT_TIMEOUT_SEC = 120.0


def _resolve_base_url() -> str:
    return (
        os.getenv("ZHIPU_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
        or DEFAULT_ZHIPU_BASE_URL
    )


def _resolve_timeout() -> float:
    raw = os.getenv("ZHIPU_TIMEOUT") or os.getenv("OPENAI_TIMEOUT") or ""
    raw = raw.strip()
    if raw:
        return float(raw)
    return DEFAULT_TIMEOUT_SEC


def _get_api_key() -> str:
    key = os.getenv("ZHIPU_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError(
            "未检测到 API Key。请先设置环境变量 ZHIPU_API_KEY，例如：\n"
            "  PowerShell: $env:ZHIPU_API_KEY=\"你的智谱Key\"\n"
            "  cmd:        set ZHIPU_API_KEY=你的智谱Key\n"
            "申请地址: https://open.bigmodel.cn/usercenter/apikeys"
        )
    return key


def build_client() -> OpenAI:
    api_key = _get_api_key()
    return OpenAI(
        api_key=api_key,
        base_url=_resolve_base_url(),
        timeout=_resolve_timeout(),
    )


def _optional_float(name: str) -> float | None:
    raw = os.getenv(name, "").strip()
    return float(raw) if raw else None


def _optional_int(name: str) -> int | None:
    raw = os.getenv(name, "").strip()
    return int(raw) if raw else None


@dataclass
class SessionConfig:
    model: str
    base_url: str
    temperature: float | None
    max_tokens: int | None
    api_key_set: bool


@dataclass
class TurnUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class TurnRecord:
    """单轮对话完整记录（供机制查看器浏览历史）。"""
    round: int
    request: dict[str, Any]
    response: dict[str, Any] | None
    messages_after: list[dict]
    usage: TurnUsage | None = None
    error: str | None = None


@dataclass
class MechanismSnapshot:
    """一轮对话后的机制关键值（教学用）。"""
    round: int
    messages_count: int
    user_assistant_pairs: int
    approx_chars_in_messages: int
    last_usage: TurnUsage | None
    cumulative_prompt_tokens: int
    cumulative_completion_tokens: int
    cumulative_total_tokens: int
    config: SessionConfig
    messages: list[dict] = field(repr=False)
    last_request: dict[str, Any] | None = None
    last_response: dict[str, Any] | None = None


def load_config() -> SessionConfig:
    return SessionConfig(
        model=os.getenv("ZHIPU_MODEL") or os.getenv("OPENAI_MODEL", DEFAULT_ZHIPU_MODEL),
        base_url=_resolve_base_url(),
        temperature=_optional_float("OPENAI_TEMPERATURE"),
        max_tokens=_optional_int("OPENAI_MAX_TOKENS"),
        api_key_set=bool(os.getenv("ZHIPU_API_KEY") or os.getenv("OPENAI_API_KEY")),
    )


class AgentSession:
    def __init__(self) -> None:
        self.config = load_config()
        self.client = build_client()
        self.messages: list[dict] = []
        self.round_count = 0
        self.cumulative_prompt = 0
        self.cumulative_completion = 0
        self.cumulative_total = 0
        self._last_usage: TurnUsage | None = None
        self._last_request: dict[str, Any] | None = None
        self._last_response: dict[str, Any] | None = None
        self.turn_history: list[TurnRecord] = []

    def _approx_chars(self) -> int:
        return sum(len(str(m.get("content", ""))) for m in self.messages)

    def snapshot(self) -> MechanismSnapshot:
        return MechanismSnapshot(
            round=self.round_count,
            messages_count=len(self.messages),
            user_assistant_pairs=len(self.messages) // 2,
            approx_chars_in_messages=self._approx_chars(),
            last_usage=self._last_usage,
            cumulative_prompt_tokens=self.cumulative_prompt,
            cumulative_completion_tokens=self.cumulative_completion,
            cumulative_total_tokens=self.cumulative_total,
            config=self.config,
            messages=list(self.messages),
            last_request=self._last_request,
            last_response=self._last_response,
        )

    @staticmethod
    def _serialize_api_response(response: Any) -> dict[str, Any]:
        if hasattr(response, "model_dump"):
            return response.model_dump()
        if hasattr(response, "dict"):
            return response.dict()
        return {"raw": repr(response)}

    def chat(self, user_text: str) -> tuple[str, MechanismSnapshot]:
        self.messages.append({"role": "user", "content": user_text})
        body: dict[str, Any] = {
            "model": self.config.model,
            "messages": copy.deepcopy(self.messages),
        }
        if self.config.temperature is not None:
            body["temperature"] = self.config.temperature
        if self.config.max_tokens is not None:
            body["max_tokens"] = self.config.max_tokens

        self._last_request = {
            "method": "POST",
            "path": "/chat/completions",
            "base_url": self.config.base_url,
            "body": body,
        }

        response = self.client.chat.completions.create(**body)
        self._last_response = self._serialize_api_response(response)
        assistant_text = response.choices[0].message.content or ""
        self.messages.append({"role": "assistant", "content": assistant_text})

        usage = getattr(response, "usage", None)
        self._last_usage = None
        if usage is not None:
            self._last_usage = TurnUsage(
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
            )
            self.cumulative_prompt += usage.prompt_tokens
            self.cumulative_completion += usage.completion_tokens
            self.cumulative_total += usage.total_tokens

        self.round_count += 1
        self.turn_history.append(
            TurnRecord(
                round=self.round_count,
                request=copy.deepcopy(self._last_request),
                response=copy.deepcopy(self._last_response),
                messages_after=copy.deepcopy(self.messages),
                usage=self._last_usage,
            )
        )
        return assistant_text, self.snapshot()

    def rollback_last_user(self) -> None:
        if self.messages and self.messages[-1].get("role") == "user":
            self.messages.pop()

    def reset(self) -> MechanismSnapshot:
        self.messages.clear()
        self.round_count = 0
        self.cumulative_prompt = 0
        self.cumulative_completion = 0
        self.cumulative_total = 0
        self._last_usage = None
        self._last_request = None
        self._last_response = None
        self.turn_history.clear()
        return self.snapshot()

    def record_failed_turn(self, error: str) -> None:
        """API 失败时记入历史（便于在原始报文中查看失败请求）。"""
        if not self._last_request:
            return
        self.turn_history.append(
            TurnRecord(
                round=self.round_count + 1,
                request=copy.deepcopy(self._last_request),
                response=None,
                messages_after=copy.deepcopy(self.messages),
                usage=None,
                error=error,
            )
        )
