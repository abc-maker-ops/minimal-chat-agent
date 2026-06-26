# -*- coding: utf-8 -*-
"""工具 schema 与分发（calculator + 文件工具 + done）。"""
from __future__ import annotations

import json
from typing import Any

from calculator import eval_expression
from done_validator import validate_delivery
from file_tools import list_dir, read_file, write_text

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

READ_FILE_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "读取工作区内 UTF-8 文本文件，返回文件内容作为 Observation。",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "相对工作区路径，例如 input/note_a.txt",
                }
            },
            "required": ["path"],
        },
    },
}

LIST_DIR_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "list_dir",
        "description": "列出工作区目录下的文件名（子目录以 / 结尾）。",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "相对工作区目录，空字符串表示根目录",
                }
            },
            "required": [],
        },
    },
}

WRITE_TEXT_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "write_text",
        "description": (
            "将 UTF-8 文本写入工作区 output/ 下路径。"
            "交付 Markdown、JSON、XML 等结构化文件时使用。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "须以 output/ 开头，例如 output/summary.md",
                },
                "content": {
                    "type": "string",
                    "description": "完整文件正文",
                },
            },
            "required": ["path", "content"],
        },
    },
}

DONE_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "done",
        "description": (
            "机器验收交付文件是否符合结构化规则。"
            "返回 JSON 字符串：{\"ok\": true/false, \"message\": \"...\"}。"
            "任务完成前须调用且 ok 为 true。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "待验收的相对路径，例如 output/summary.md",
                },
                "format": {
                    "type": "string",
                    "enum": ["markdown", "json", "xml"],
                    "description": "交付物格式",
                },
                "required_headings": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Markdown 时必填标题列表，如 [\"## 结论\"]",
                },
                "required_keys": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON 时必填字段名列表",
                },
                "root_tag": {
                    "type": "string",
                    "description": "XML 时要求的根元素名",
                },
            },
            "required": ["path", "format"],
        },
    },
}

TOOL_SCHEMAS: list[dict[str, Any]] = [
    CALCULATOR_TOOL,
    READ_FILE_TOOL,
    LIST_DIR_TOOL,
    WRITE_TEXT_TOOL,
    DONE_TOOL,
]


def _parse_args(arguments: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return None, "错误：工具参数不是合法 JSON"
    if not isinstance(payload, dict):
        return None, "错误：工具参数必须是 JSON 对象"
    return payload, None


def run_tool(name: str, arguments: str) -> str:
    """按 tool_calls 中的函数名分发；始终把字符串 Observation 写回 messages。"""
    payload, err = _parse_args(arguments)
    if err:
        return err

    if name == "calculator":
        expression = str(payload.get("expression", "")).strip()
        text, ok = eval_expression(expression)
        return text

    if name == "read_file":
        text, ok = read_file(str(payload.get("path", "")).strip())
        return text

    if name == "list_dir":
        text, ok = list_dir(str(payload.get("path", "")).strip())
        return text

    if name == "write_text":
        path = str(payload.get("path", "")).strip()
        content = payload.get("content", "")
        if not isinstance(content, str):
            content = str(content)
        text, ok = write_text(path, content)
        return text

    if name == "done":
        path = str(payload.get("path", "")).strip()
        fmt = str(payload.get("format", "")).strip()
        rules: dict[str, Any] = {}
        if payload.get("required_headings") is not None:
            rules["required_headings"] = payload.get("required_headings")
        if payload.get("required_keys") is not None:
            rules["required_keys"] = payload.get("required_keys")
        if payload.get("root_tag") is not None:
            rules["root_tag"] = payload.get("root_tag")
        text, ok = validate_delivery(path, fmt, rules)
        return text

    return f"错误：未知工具 {name!r}"
