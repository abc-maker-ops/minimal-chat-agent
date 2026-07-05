# -*- coding: utf-8 -*-
"""工具 JSON Schema 与分发（v8：description 工程化 + 参数校验）。"""
from __future__ import annotations

import json
import os
from typing import Any

from calculator import eval_expression
from done_validator import validate_delivery
from file_tools import list_dir, read_file, write_text


def _schema_profile() -> str:
    return (os.getenv("TOOL_SCHEMA_PROFILE") or "good").strip().lower()


def _read_file_schema(*, good: bool) -> dict[str, Any]:
    if good:
        desc = (
            "读取工作区内 UTF-8 文本文件全文。"
            "path 须为相对工作区根目录的路径，例如 input/note_a.txt 或 input/note_b.txt。"
            "不要猜测绝对路径；文件不存在时 Observation 以「错误：」开头。"
        )
        path_desc = "相对路径，例如 input/note_a.txt"
    else:
        desc = "读取工作区内 UTF-8 文本文件，返回文件内容作为 Observation。"
        path_desc = "文件路径"
    return {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": desc,
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": path_desc},
                },
                "required": ["path"],
            },
        },
    }


def _list_dir_schema(*, good: bool) -> dict[str, Any]:
    if good:
        desc = (
            "列出工作区某目录下的条目名；子目录以 / 结尾。"
            "探索 input/ 或 output/ 时优先调用；path 为空字符串表示工作区根。"
        )
        path_desc = "相对目录，空字符串表示根目录，例如 input/"
    else:
        desc = "列出工作区目录下的文件名（子目录以 / 结尾）。"
        path_desc = "相对工作区目录，空字符串表示根目录"
    return {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": desc,
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": path_desc},
                },
                "required": [],
            },
        },
    }


def _write_text_schema(*, good: bool) -> dict[str, Any]:
    if good:
        desc = (
            "将 UTF-8 文本写入工作区 output/ 下路径；须以 output/ 开头，"
            "例如 output/summary.md 或 output/result.json。"
            "content 为完整文件正文；写入成功后才能调用 done 验收。"
        )
        path_desc = "须以 output/ 开头，例如 output/summary.md"
    else:
        desc = "将 UTF-8 文本写入工作区 output/ 下路径。交付 Markdown、JSON、XML 等结构化文件时使用。"
        path_desc = "须以 output/ 开头，例如 output/summary.md"
    return {
        "type": "function",
        "function": {
            "name": "write_text",
            "description": desc,
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": path_desc},
                    "content": {"type": "string", "description": "完整文件正文"},
                },
                "required": ["path", "content"],
            },
        },
    }


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

DONE_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "done",
        "description": (
            "机器验收交付文件是否符合结构化规则。"
            "返回 JSON 字符串：{\"ok\": true/false, \"message\": \"...\", \"missing\": [...]}。"
            "write_text 成功后须调用；ok 为 false 时读 missing 再补写。"
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


def build_tool_schemas() -> list[dict[str, Any]]:
    good = _schema_profile() != "legacy"
    return [
        CALCULATOR_TOOL,
        _read_file_schema(good=good),
        _list_dir_schema(good=good),
        _write_text_schema(good=good),
        DONE_TOOL,
    ]


TOOL_SCHEMAS: list[dict[str, Any]] = build_tool_schemas()


def _parse_args(arguments: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return None, "错误：工具参数不是合法 JSON"
    if not isinstance(payload, dict):
        return None, "错误：工具参数必须是 JSON 对象"
    return payload, None


def validate_tool_args(name: str, payload: dict[str, Any]) -> str | None:
    """程序侧轻量校验，补充 JSON Schema 未能拦截的明显错误。"""
    if name == "read_file":
        path = str(payload.get("path", "")).strip()
        if not path:
            return "错误：read_file 缺少 path"
        if path.startswith("/") or ".." in path.replace("\\", "/"):
            return "错误：path 须为工作区内相对路径"
    if name == "write_text":
        path = str(payload.get("path", "")).strip()
        if not path.startswith("output/"):
            return "错误：write_text 的 path 须以 output/ 开头"
    return None


def run_tool(name: str, arguments: str) -> str:
    payload, err = _parse_args(arguments)
    if err:
        return err

    extra = validate_tool_args(name, payload)
    if extra:
        return extra

    if name == "calculator":
        text, _ = eval_expression(str(payload.get("expression", "")).strip())
        return text

    if name == "read_file":
        text, _ = read_file(str(payload.get("path", "")).strip())
        return text

    if name == "list_dir":
        text, _ = list_dir(str(payload.get("path", "")).strip())
        return text

    if name == "write_text":
        path = str(payload.get("path", "")).strip()
        content = payload.get("content", "")
        if not isinstance(content, str):
            content = str(content)
        text, _ = write_text(path, content)
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
        text, _ = validate_delivery(path, fmt, rules)
        return text

    return f"错误：未知工具 {name!r}"
