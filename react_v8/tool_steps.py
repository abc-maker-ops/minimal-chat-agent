# -*- coding: utf-8 -*-
"""单步 ReAct：模型发起 tool_call 与程序返回 Observation。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolStep:
    step: int
    tool_name: str
    arguments: str
    observation: str
    ok: bool
    react_round: int = 0
    parallel_group: int | None = None
