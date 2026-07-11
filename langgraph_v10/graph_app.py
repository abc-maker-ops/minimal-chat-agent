# -*- coding: utf-8 -*-
"""编译 LangGraph：agent ↔ tools 环 + forced done 分支。"""
from __future__ import annotations

import os

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from bridge_v8 import ReactContext, should_force_done_after_text_exit
from llm_factory import build_chat_model
from nodes import force_done_gate, make_agent_node, tools_node
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

    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
        "agent",
        _route_after_agent,
        {
            "tools": "tools",
            "force_done": "force_done_gate",
            "end": END,
        },
    )
    graph.add_edge("force_done_gate", "agent")
    graph.add_conditional_edges(
        "tools",
        _route_after_tools,
        {"agent": "agent", "end": END},
    )

    checkpointer = MemorySaver() if with_checkpoint else None
    return graph.compile(checkpointer=checkpointer)


def run_graph(
    initial_state: AgentState,
    *,
    llm: ChatOpenAI | None = None,
    thread_id: str | None = None,
    with_checkpoint: bool = False,
) -> AgentState:
    app = build_graph(llm=llm, with_checkpoint=with_checkpoint or bool(thread_id))
    config: dict = {"recursion_limit": resolve_max_graph_steps() * 3 + 4}
    if thread_id:
        config["configurable"] = {"thread_id": thread_id}
    result = app.invoke(initial_state, config=config)
    if isinstance(result, dict):
        return result
    return dict(result)
