# -*- coding: utf-8 -*-
"""LangGraph 节点：agent（LangChain bind_tools）与 tools（复用 v8 run_tool）。"""
from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage
from langchain_openai import ChatOpenAI

from bridge_v8 import (
    ReactContext,
    ToolStep,
    TOOL_SCHEMAS,
    resolve_tool_policy,
    run_tool,
)
from state import AgentState


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

        bound = llm.bind_tools(TOOL_SCHEMAS, tool_choice=policy.tool_choice)
        try:
            if policy.parallel_tool_calls:
                response = bound.invoke(state["messages"])
            else:
                response = bound.invoke(state["messages"], parallel_tool_calls=False)
        except TypeError:
            response = bound.invoke(state["messages"])

        if not isinstance(response, AIMessage):
            response = AIMessage(content=str(response))

        return {
            "messages": [response],
            "node_path": ["agent"],
            "policy_labels": [label],
            "react_round": react_round + 1,
            "force_done_pending": False,
        }

    return agent_node


def tools_node(state: AgentState) -> dict[str, Any]:
    last = state["messages"][-1]
    if not isinstance(last, AIMessage) or not last.tool_calls:
        return {"node_path": ["tools(empty)"]}

    tool_messages: list[ToolMessage] = []
    steps: list[ToolStep] = []
    has_written = bool(state.get("has_written"))
    done_ok = state.get("done_ok")
    start = len(state.get("tool_steps") or []) + 1
    react_round = int(state.get("react_round") or 1)

    for idx, tc in enumerate(last.tool_calls):
        tc_id, name, args_json = _tool_call_parts(tc)
        observation = run_tool(name, args_json)
        ok = _observation_ok(observation, name)
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
                parallel_group=None,
            )
        )
        tool_messages.append(
            ToolMessage(content=observation, tool_call_id=tc_id, name=name)
        )

    return {
        "messages": tool_messages,
        "has_written": has_written,
        "done_ok": done_ok,
        "tool_steps": steps,
        "node_path": ["tools"],
    }


def force_done_gate(state: AgentState) -> dict[str, Any]:
    return {
        "force_done_pending": True,
        "node_path": ["force_done_gate"],
    }
