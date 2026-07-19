# -*- coding: utf-8 -*-
"""将 v8 业务工具封装为 LangChain StructuredTool，供 bind_tools 使用。"""
from __future__ import annotations

import json
from typing import Any, List, Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, create_model

from bridge_v8 import TOOL_SCHEMAS, run_tool


def _field_type(spec: dict[str, Any]) -> Any:
    t = spec.get("type")
    if t == "array":
        return List[str]
    if t == "object":
        return dict
    return str


def _openai_schema_to_args_model(name: str, parameters: dict[str, Any]) -> type[BaseModel]:
    props = parameters.get("properties") or {}
    required = set(parameters.get("required") or [])
    fields: dict[str, Any] = {}
    for key, spec in props.items():
        desc = str(spec.get("description") or key)
        py_t = _field_type(spec)
        if key in required:
            fields[key] = (py_t, Field(description=desc))
        else:
            fields[key] = (Optional[py_t], Field(default=None, description=desc))
    if not fields:
        fields["_unused"] = (Optional[str], Field(default=None, description="占位"))
    return create_model(f"{name}Args", **fields)  # type: ignore[call-overload]


def _make_runner(tool_name: str):
    def _run(**kwargs: Any) -> str:
        clean = {k: v for k, v in kwargs.items() if v is not None and k != "_unused"}
        return run_tool(tool_name, json.dumps(clean, ensure_ascii=False))

    return _run


def build_langchain_tools() -> list[StructuredTool]:
    """从 v8 TOOL_SCHEMAS 生成 StructuredTool；执行仍走同一 run_tool。"""
    tools: list[StructuredTool] = []
    for item in TOOL_SCHEMAS:
        fn = item.get("function") or {}
        name = str(fn.get("name") or "")
        if not name:
            continue
        desc = str(fn.get("description") or name)
        args_model = _openai_schema_to_args_model(name, fn.get("parameters") or {})
        tools.append(
            StructuredTool.from_function(
                func=_make_runner(name),
                name=name,
                description=desc,
                args_schema=args_model,
            )
        )
    return tools


LC_TOOLS: list[StructuredTool] = build_langchain_tools()
