# -*- coding: utf-8 -*-
"""LangGraph 状态：messages + 业务字段 + 图轨迹。"""
from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from bridge_v8 import ToolStep


class AgentState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    has_written: bool
    done_ok: bool | None
    user_requires_done: bool
    react_round: int
    force_done_pending: bool
    node_path: Annotated[list[str], operator.add]
    policy_labels: Annotated[list[str], operator.add]
    tool_steps: Annotated[list[ToolStep], operator.add]
    final_text: str
    hit_limit: bool


def state_summary(state: AgentState) -> dict[str, Any]:
    msgs = state.get("messages") or []
    return {
        "react_round": state.get("react_round", 0),
        "has_written": state.get("has_written", False),
        "done_ok": state.get("done_ok"),
        "message_count": len(msgs),
        "node_path": " → ".join(state.get("node_path") or []),
    }
