# -*- coding: utf-8 -*-
"""tool_choice / parallel_tool_calls / forced tool 策略（第 09 篇）。"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolPolicy:
    """单次 LLM 调用的工具策略。"""

    tool_choice: str | dict[str, Any]
    parallel_tool_calls: bool
    client_parallel: bool
    label: str = ""


@dataclass
class ReactContext:
    react_round: int
    has_written_output: bool
    done_ok: bool | None
    user_requires_done: bool = False


def _env_bool(name: str, default: bool) -> bool:
    raw = (os.getenv(name) or ("1" if default else "0")).strip().lower()
    return raw not in ("0", "false", "no", "off")


def resolve_tool_policy(
    ctx: ReactContext,
    *,
    force_done: bool = False,
    tools_disabled: bool = False,
) -> ToolPolicy:
    """按 ReAct 轮次与任务状态选择 tool_choice 与并行开关。"""
    if tools_disabled:
        return ToolPolicy(
            tool_choice="none",
            parallel_tool_calls=False,
            client_parallel=False,
            label="none（禁止工具）",
        )

    if force_done:
        return ToolPolicy(
            tool_choice={"type": "function", "function": {"name": "done"}},
            parallel_tool_calls=False,
            client_parallel=False,
            label="forced done",
        )

    parallel = _env_bool("PARALLEL_TOOL_CALLS", True)
    first_choice = (os.getenv("TOOL_CHOICE_FIRST") or "required").strip().lower()

    if ctx.react_round == 0 and first_choice == "required":
        return ToolPolicy(
            tool_choice="required",
            parallel_tool_calls=parallel,
            client_parallel=parallel,
            label="required（首轮须调工具）",
        )

    if ctx.react_round == 0 and first_choice.startswith("{"):
        # 允许实验：TOOL_CHOICE_FIRST={"type":"function","function":{"name":"list_dir"}}
        import json

        try:
            forced = json.loads(first_choice)
            return ToolPolicy(
                tool_choice=forced,
                parallel_tool_calls=parallel,
                client_parallel=parallel,
                label=f"forced {forced.get('function', {}).get('name', '?')}",
            )
        except json.JSONDecodeError:
            pass

    return ToolPolicy(
        tool_choice="auto",
        parallel_tool_calls=parallel,
        client_parallel=parallel,
        label="auto",
    )


def should_force_done_after_text_exit(ctx: ReactContext) -> bool:
    """已写入交付物但 done 未通过，且模型试图纯文字收尾时，程序强制再调 done。"""
    if not _env_bool("FORCE_DONE_ON_TEXT_EXIT", True):
        return False
    if not ctx.has_written_output:
        return False
    if ctx.done_ok is True:
        return False
    return ctx.user_requires_done or ctx.done_ok is False
