# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolStep:
    """单步 ReAct：模型发起 tool_call 与程序返回 Observation。"""

    step: int
    tool_name: str
    arguments: str
    observation: str
    ok: bool
