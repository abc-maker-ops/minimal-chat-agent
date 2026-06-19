# -*- coding: utf-8 -*-
"""工具 schema 与分发。"""
from __future__ import annotations

import json
from typing import Any

from calculator import eval_expression

CALCULATOR_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "calculator",
        "description": (
            "安全计算四则运算算术表达式，仅含数字、+ - * / 与括号。"
            "示例：(23+19)*2"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "算术表达式，例如 \"23+19\" 或 \"(10+5)*3\"",
                }
            },
            "required": ["expression"],
        },
    },
}

TOOL_SCHEMAS: list[dict[str, Any]] = [CALCULATOR_TOOL]


def run_tool(name: str, arguments: str) -> str:
    if name != "calculator":
        return f"错误：未知工具 {name!r}"
    try:
        payload = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return "错误：工具参数不是合法 JSON"
    if not isinstance(payload, dict):
        return "错误：工具参数必须是 JSON 对象"
    expression = str(payload.get("expression", "")).strip()
    text, ok = eval_expression(expression)
    if ok:
        return text
    return text
