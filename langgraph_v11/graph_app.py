# -*- coding: utf-8 -*-
"""编译 LangGraph：agent ↔ tools 环 + 人审 + forced done；检查点续跑。"""
from __future__ import annotations

import os
from typing import Any

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from bridge_v8 import ReactContext, should_force_done_after_text_exit
from llm_factory import build_chat_model
from nodes import (
    _human_gate_enabled,
    _needs_human_approval,
    force_done_gate,
    human_gate_node,
    make_agent_node,
    tools_node,
)
from state import AgentState


def resolve_max_graph_steps() -> int:
    raw = (os.getenv("MAX_REACT_STEPS") or os.getenv("MAX_GRAPH_STEPS") or "10").strip()
    try:
        n = int(raw)
    except ValueError:
        n = 10
    return max(1, min(n, 24))


def _route_after_agent(state: AgentState) -> str:
    max_steps = resolve_max_graph_steps()
    react_round = int(state.get("react_round") or 0)
    if react_round >= max_steps:
        return "end"

    last = state["messages"][-1]
    tool_calls = getattr(last, "tool_calls", None) or []
    if tool_calls:
        names = list(state.get("pending_tool_names") or [])
        if _needs_human_approval(names):
            return "human"
        return "tools"

    ctx = ReactContext(
        react_round=max(0, react_round - 1),
        has_written_output=bool(state.get("has_written")),
        done_ok=state.get("done_ok"),
        user_requires_done=bool(state.get("user_requires_done")),
    )
    if should_force_done_after_text_exit(ctx) and react_round < max_steps:
        return "force_done"
    return "end"


def _route_after_human(state: AgentState) -> str:
    if state.get("human_approved") is False:
        return "end"
    return "tools"


def _route_after_tools(state: AgentState) -> str:
    max_steps = resolve_max_graph_steps()
    react_round = int(state.get("react_round") or 0)
    if react_round >= max_steps:
        return "end"
    return "agent"


def build_graph(*, llm: ChatOpenAI | None = None, with_checkpoint: bool = False):
    llm = llm or build_chat_model()
    graph = StateGraph(AgentState)
    graph.add_node("agent", make_agent_node(llm))
    graph.add_node("tools", tools_node)
    graph.add_node("force_done_gate", force_done_gate)
    graph.add_node("human_gate", human_gate_node)

    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
        "agent",
        _route_after_agent,
        {
            "tools": "tools",
            "human": "human_gate",
            "force_done": "force_done_gate",
            "end": END,
        },
    )
    graph.add_edge("force_done_gate", "agent")
    graph.add_conditional_edges(
        "human_gate",
        _route_after_human,
        {"tools": "tools", "end": END},
    )
    graph.add_conditional_edges(
        "tools",
        _route_after_tools,
        {"agent": "agent", "end": END},
    )

    # 人审 interrupt 必须配合 checkpointer；显式开启或启用 HUMAN_GATE 时打开
    need_ckpt = with_checkpoint or _human_gate_enabled()
    checkpointer = MemorySaver() if need_ckpt else None
    return graph.compile(checkpointer=checkpointer)


def _has_interrupt(result: Any) -> bool:
    if isinstance(result, dict) and result.get("__interrupt__"):
        return True
    return False


def run_graph(
    initial_state: AgentState,
    *,
    llm: ChatOpenAI | None = None,
    thread_id: str | None = None,
    with_checkpoint: bool = False,
    resume_value: Any = None,
    approval_fn=None,
) -> AgentState:
    """运行图；若命中 human_gate interrupt，则调用 approval_fn 后 Command(resume=...)。"""
    use_ckpt = with_checkpoint or bool(thread_id) or _human_gate_enabled()
    app = build_graph(llm=llm, with_checkpoint=use_ckpt)
    config: dict = {"recursion_limit": resolve_max_graph_steps() * 3 + 8}
    tid = thread_id or "default"
    if use_ckpt:
        config["configurable"] = {"thread_id": tid}

    if resume_value is not None:
        result = app.invoke(Command(resume=resume_value), config=config)
    else:
        result = app.invoke(initial_state, config=config)

    # 自动/交互式处理人审打断（可多轮）
    guard = 0
    while _has_interrupt(result) and guard < 8:
        guard += 1
        payload = result["__interrupt__"][0].value
        if approval_fn is not None:
            decision = approval_fn(payload)
        else:
            auto = os.getenv("AUTO_APPROVE", "1").strip().lower() in ("1", "true", "yes")
            decision = True if auto else False
        result = app.invoke(Command(resume=decision), config=config)

    if isinstance(result, dict):
        # 去掉内部字段再返回
        out = {k: v for k, v in result.items() if k != "__interrupt__"}
        return out  # type: ignore[return-value]
    return dict(result)
