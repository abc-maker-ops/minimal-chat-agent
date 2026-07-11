# -*- coding: utf-8 -*-
"""复用 react_v8 工具、策略与工作区（第 10 篇不重写业务工具）。"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_LAB = Path(__file__).resolve().parent.parent
_V8 = _LAB / "react_v8"
_V10 = Path(__file__).resolve().parent

for p in (str(_LAB / "minimal_chat_v1"), str(_V8), str(_V10)):
    if p not in sys.path:
        sys.path.insert(0, p)


def _load_v8(name: str, filename: str):
    qual = f"langgraph_v10_bridge_{name}"
    if qual in sys.modules:
        return sys.modules[qual]
    spec = importlib.util.spec_from_file_location(qual, _V8 / filename)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载 react_v8/{filename}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[qual] = mod
    spec.loader.exec_module(mod)
    return mod


_tool_registry = _load_v8("tool_registry", "tool_registry.py")
_tool_policy = _load_v8("tool_policy", "tool_policy.py")
_task_router = _load_v8("task_router", "task_router.py")
_workspace = _load_v8("workspace", "workspace.py")
_tool_steps = _load_v8("tool_steps", "tool_steps.py")

TOOL_SCHEMAS = _tool_registry.TOOL_SCHEMAS
run_tool = _tool_registry.run_tool
ReactContext = _tool_policy.ReactContext
ToolPolicy = _tool_policy.ToolPolicy
resolve_tool_policy = _tool_policy.resolve_tool_policy
should_force_done_after_text_exit = _tool_policy.should_force_done_after_text_exit
TaskRoute = _task_router.TaskRoute
analyze_task = _task_router.analyze_task
workspace_root = _workspace.workspace_root
ToolStep = _tool_steps.ToolStep
