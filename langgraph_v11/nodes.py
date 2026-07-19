# -*- coding: utf-8 -*-
"""LangGraph 节点：agent（LC StructuredTool）/ tools（可并行）/ human_gate / force_done。"""
from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.types import interrupt

from bridge_v8 import (
    PARALLEL_SAFE_TOOLS,
    ReactContext,
    ToolStep,
    can_run_parallel,
    resolve_tool_policy,
    run_tool,
)
from lc_tools import LC_TOOLS
from state import AgentState


def _human_gate_enabled() -> bool:
    return os.getenv("HUMAN_GATE", "").strip().lower() in ("1", "true", "yes")


def _observation_ok(observation: str, tool_name: str) -> bool:
    if observation.startswith("错误："):
        return False
    if tool_name == "done":
        try:
            data = json.loads(observation)
            return bool(data.get("ok"))
        except json.JSONDecodeError:
            return False
    return True


def _tool_call_parts(tc: Any) -> tuple[str, str, str]:
    if isinstance(tc, dict):
        return (
            str(tc.get("id", "")),
            str(tc.get("name", "")),
            json.dumps(tc.get("args") or {}, ensure_ascii=False),
        )
    return (
        str(getattr(tc, "id", "")),
        str(getattr(tc, "name", "")),
        json.dumps(getattr(tc, "args", {}) or {}, ensure_ascii=False),
    )


def _tool_names(tool_calls: list[Any]) -> list[str]:
    return [_tool_call_parts(tc)[1] for tc in tool_calls]


def _needs_human_approval(tool_names: list[str]) -> bool:
    if not _human_gate_enabled():
        return False
    return any(n in ("write_text", "done") for n in tool_names)


def make_agent_node(llm: ChatOpenAI):
    def agent_node(state: AgentState) -> dict[str, Any]:
        react_round = int(state.get("react_round") or 0)
        ctx = ReactContext(
            react_round=react_round,
            has_written_output=bool(state.get("has_written")),
            done_ok=state.get("done_ok"),
            user_requires_done=bool(state.get("user_requires_done")),
        )
        force = bool(state.get("force_done_pending"))
        policy = resolve_tool_policy(ctx, force_done=force)
        label = f"R{react_round + 1}:{policy.label}"

        # 第 11 篇：绑 StructuredTool，不再直接绑 OpenAI dict Schema
        bound = llm.bind_tools(LC_TOOLS, tool_choice=policy.tool_choice)
        try:
            if policy.parallel_tool_calls:
                response = bound.invoke(state["messages"])
            else:
                response = bound.invoke(state["messages"], parallel_tool_calls=False)
        except TypeError:
            response = bound.invoke(state["messages"])

        if not isinstance(response, AIMessage):
            response = AIMessage(content=str(response))

        names = _tool_names(list(response.tool_calls or []))
        return {
            "messages": [response],
            "node_path": ["agent"],
            "policy_labels": [label],
            "react_round": react_round + 1,
            "force_done_pending": False,
            "pending_tool_names": names,
            "human_approved": None,
        }

    return agent_node


def human_gate_node(state: AgentState) -> dict[str, Any]:
    names = list(state.get("pending_tool_names") or [])
    decision = interrupt(
        {
            "type": "approve_tool_batch",
            "message": "即将执行写文件或 done 验收，是否批准？",
            "tool_names": names,
        }
    )
    if isinstance(decision, dict):
        approved = bool(decision.get("approved", decision.get("ok", False)))
    else:
        approved = bool(decision)
    return {
        "human_approved": approved,
        "node_path": ["human_gate"],
    }


def tools_node(state: AgentState) -> dict[str, Any]:
    last = state["messages"][-1]
    if not isinstance(last, AIMessage) or not last.tool_calls:
        return {"node_path": ["tools(empty)"]}

    if state.get("human_approved") is False:
        rejected = []
        for tc in last.tool_calls:
            tc_id, name, _ = _tool_call_parts(tc)
            rejected.append(
                ToolMessage(
                    content="错误：人工审批未通过，本批工具未执行。",
                    tool_call_id=tc_id,
                    name=name,
                )
            )
        return {
            "node_path": ["tools(rejected)"],
            "messages": rejected,
            "pending_tool_names": [],
            "human_approved": None,
        }

    tool_calls = list(last.tool_calls)
    names = _tool_names(tool_calls)
    react_round = int(state.get("react_round") or 1)
    start = len(state.get("tool_steps") or []) + 1
    use_parallel = can_run_parallel(names) and all(n in PARALLEL_SAFE_TOOLS for n in names)
    # 环境变量可强制关闭并行（对照实验）
    if os.getenv("PARALLEL_TOOL_CALLS", "1").strip().lower() in ("0", "false", "no"):
        use_parallel = False
    group_id = react_round if use_parallel else None

    def _one(tc: Any) -> tuple[str, str, str, str, bool]:
        tc_id, name, args_json = _tool_call_parts(tc)
        observation = run_tool(name, args_json)
        ok = _observation_ok(observation, name)
        return tc_id, name, args_json, observation, ok

    if use_parallel:
        with ThreadPoolExecutor(max_workers=min(4, len(tool_calls))) as pool:
            raw_results = list(pool.map(_one, tool_calls))
    else:
        raw_results = [_one(tc) for tc in tool_calls]

    tool_messages: list[ToolMessage] = []
    steps: list[ToolStep] = []
    has_written = bool(state.get("has_written"))
    done_ok = state.get("done_ok")

    for idx, (tc_id, name, args_json, observation, ok) in enumerate(raw_results):
        if name == "done":
            done_ok = ok
        if name == "write_text" and ok:
            has_written = True
        steps.append(
            ToolStep(
                step=start + idx,
                tool_name=name,
                arguments=args_json,
                observation=observation,
                ok=ok,
                react_round=react_round,
                parallel_group=group_id,
            )
        )
        tool_messages.append(
            ToolMessage(content=observation, tool_call_id=tc_id, name=name)
        )

    path_label = f"tools(parallel:{group_id})" if group_id else "tools"
    return {
        "messages": tool_messages,
        "has_written": has_written,
        "done_ok": done_ok,
        "tool_steps": steps,
        "node_path": [path_label],
        "last_parallel_group": group_id,
        "human_approved": None,
        "pending_tool_names": [],
    }


def force_done_gate(state: AgentState) -> dict[str, Any]:
    return {
        "force_done_pending": True,
        "node_path": ["force_done_gate"],
    }
