# -*- coding: utf-8 -*-
"""单步 ReAct：模型发起 tool_call 与程序返回 Observation。

ok 含义因工具而异：普通工具看 observation 是否不以「错误：」开头；
done 工具在 prompt_session._observation_ok 中另解析 JSON 的 ok 字段。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolStep:
    step: int
    tool_name: str
    arguments: str
    observation: str
    ok: bool
