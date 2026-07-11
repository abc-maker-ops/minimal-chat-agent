# -*- coding: utf-8 -*-
"""dict messages（机制查看器）与 LangChain BaseMessage 互转。"""
from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)


def dicts_to_lc(messages: list[dict[str, Any]]) -> list[BaseMessage]:
    out: list[BaseMessage] = []
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content") or ""
        if role == "system":
            out.append(SystemMessage(content=content))
        elif role == "user":
            out.append(HumanMessage(content=content))
        elif role == "assistant":
            tool_calls = msg.get("tool_calls") or []
            lc_calls: list[dict[str, Any]] = []
            for tc in tool_calls:
                fn = tc.get("function") or {}
                args_raw = fn.get("arguments") or "{}"
                try:
                    args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
                except json.JSONDecodeError:
                    args = {}
                lc_calls.append(
                    {
                        "id": tc.get("id", ""),
                        "name": fn.get("name", ""),
                        "args": args if isinstance(args, dict) else {},
                    }
                )
            out.append(AIMessage(content=content, tool_calls=lc_calls))
        elif role == "tool":
            out.append(
                ToolMessage(
                    content=str(content),
                    tool_call_id=str(msg.get("tool_call_id", "")),
                )
            )
    return out


def lc_to_dicts(messages: list[BaseMessage]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for msg in messages:
        if isinstance(msg, SystemMessage):
            out.append({"role": "system", "content": msg.content})
        elif isinstance(msg, HumanMessage):
            out.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            row: dict[str, Any] = {
                "role": "assistant",
                "content": msg.content or "",
            }
            if msg.tool_calls:
                serialized = []
                for tc in msg.tool_calls:
                    args = tc.get("args") if isinstance(tc, dict) else getattr(tc, "args", {})
                    name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "")
                    tid = tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", "")
                    serialized.append(
                        {
                            "id": tid,
                            "type": "function",
                            "function": {
                                "name": name,
                                "arguments": json.dumps(args, ensure_ascii=False),
                            },
                        }
                    )
                row["tool_calls"] = serialized
            out.append(row)
        elif isinstance(msg, ToolMessage):
            out.append(
                {
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id,
                    "content": msg.content,
                }
            )
    return out


def final_assistant_text(messages: list[BaseMessage]) -> str:
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and not msg.tool_calls:
            text = (msg.content or "").strip()
            if text:
                return text
    return ""
