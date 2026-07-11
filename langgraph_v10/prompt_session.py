# -*- coding: utf-8 -*-
"""langgraph_v10：LangChain ChatModel + LangGraph 图编排（第 10 篇）。"""
from __future__ import annotations

import copy
import importlib.util
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Any

_LAB = Path(__file__).resolve().parent.parent
_RV5 = _LAB / "reflection_v5"
_V10 = Path(__file__).resolve().parent
sys.path.insert(0, str(_LAB / "minimal_chat_v1"))
sys.path.insert(0, str(_LAB / "role_setting_v3"))
sys.path.insert(0, str(_LAB / "reasoning_v4"))
sys.path.insert(0, str(_RV5))
sys.path.insert(0, str(_V10))

from agent_session import MechanismSnapshot  # noqa: E402
from cot_parser import parse_cot  # noqa: E402

from bridge_v8 import TaskRoute, ToolStep, analyze_task, workspace_root  # noqa: E402
from graph_app import resolve_max_graph_steps, run_graph  # noqa: E402
from messages_util import dicts_to_lc, final_assistant_text, lc_to_dicts  # noqa: E402

_rt_spec = importlib.util.spec_from_file_location(
    "langgraph_v10_runtime_trace", _V10 / "runtime_trace.py"
)
if _rt_spec is None or _rt_spec.loader is None:
    raise ImportError("无法加载 langgraph_v10/runtime_trace.py")
_rt_mod = importlib.util.module_from_spec(_rt_spec)
sys.modules["langgraph_v10_runtime_trace"] = _rt_mod
_rt_spec.loader.exec_module(_rt_mod)
RuntimeTrace = _rt_mod.RuntimeTrace
from state import AgentState  # noqa: E402

_rv5_spec = importlib.util.spec_from_file_location(
    "reflection_v5_prompt_session", _RV5 / "prompt_session.py"
)
if _rv5_spec is None or _rv5_spec.loader is None:
    raise ImportError("无法加载 reflection_v5/prompt_session.py")
_rv5_mod = importlib.util.module_from_spec(_rv5_spec)
_rv5_spec.loader.exec_module(_rv5_mod)
ReflectionAgentSession = _rv5_mod.ReflectionAgentSession


def _user_requires_done(user_text: str) -> bool:
    return bool(re.search(r"\bdone\b|验收|required_headings|required_keys", user_text, re.I))


class LangGraphAgentSession(ReflectionAgentSession):
    """v10：v8 工具表 + LangGraph 图编排。"""

    AGENT_GENERATION = 10

    def __init__(self, *, role_id: str | None = None) -> None:
        ws = _V10 / "workspace"
        os.environ.setdefault("AGENT_WORKSPACE", str(ws.resolve()))
        super().__init__(
            role_id=role_id,
            include_few_shot=True,
            include_cot=True,
            tot_enabled=False,
            force_auto=True,
            quality_mode="off",
        )
        self.last_tool_steps: tuple[ToolStep, ...] = ()
        self.graph_steps_used: int = 0
        self.graph_hit_limit: bool = False
        self.last_task_route: TaskRoute | None = None
        self.runtime_trace: RuntimeTrace | None = None
        self.last_done_ok: bool | None = None
        self.last_policy_labels: tuple[str, ...] = ()
        self.last_node_path: tuple[str, ...] = ()
        self.workspace_path = workspace_root()
        self._thread_id = str(uuid.uuid4())

    def _clear_graph_state(self) -> None:
        self.last_tool_steps = ()
        self.graph_steps_used = 0
        self.graph_hit_limit = False
        self.last_task_route = None
        self.runtime_trace = None
        self.last_done_ok = None
        self.last_policy_labels = ()
        self.last_node_path = ()

    def _run_langgraph(self, user_text: str) -> str:
        seed_messages = copy.deepcopy(self.messages)
        seed_messages.append({"role": "user", "content": user_text})

        initial: AgentState = {
            "messages": dicts_to_lc(seed_messages),
            "has_written": False,
            "done_ok": None,
            "user_requires_done": _user_requires_done(user_text),
            "react_round": 0,
            "force_done_pending": False,
            "node_path": [],
            "policy_labels": [],
            "tool_steps": [],
            "hit_limit": False,
        }

        use_ckpt = os.getenv("LANGGRAPH_CHECKPOINT", "").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        final_state = run_graph(
            initial,
            thread_id=self._thread_id if use_ckpt else None,
            with_checkpoint=use_ckpt,
        )

        self.messages = lc_to_dicts(final_state.get("messages") or [])
        self.last_tool_steps = tuple(final_state.get("tool_steps") or [])
        self.last_done_ok = final_state.get("done_ok")
        self.last_policy_labels = tuple(final_state.get("policy_labels") or [])
        self.last_node_path = tuple(final_state.get("node_path") or [])
        self.graph_steps_used = int(final_state.get("react_round") or 0)
        self.graph_hit_limit = self.graph_steps_used >= resolve_max_graph_steps()

        text = final_assistant_text(final_state.get("messages") or [])
        if self.graph_hit_limit and not text:
            text = (
                f"已达 LangGraph agent 步数上限（MAX_REACT_STEPS={resolve_max_graph_steps()}），"
                "请缩小任务或提高上限。"
            )
        return text

    def _replace_final_assistant(self, text: str) -> None:
        for i in range(len(self.messages) - 1, -1, -1):
            msg = self.messages[i]
            if msg.get("role") == "assistant" and not msg.get("tool_calls"):
                msg["content"] = text
                return

    def _maybe_refine(self, user_text: str, draft: str, route: TaskRoute) -> str:
        if not route.use_refine or not draft or draft.startswith("已达"):
            return draft
        assert self.role is not None
        system = self.role.compose_system(
            include_few_shot=self.include_few_shot,
            include_cot=self.include_cot,
        )
        self.last_draft = draft
        critique = self._run_self_critic_recorded(system, user_text, draft)
        self.last_critique = critique
        refined = self._run_refine_recorded(system, user_text, draft, critique)
        self.last_refined = refined
        self._replace_final_assistant(refined)
        return refined

    def _build_trace(self, route: TaskRoute) -> RuntimeTrace:
        return RuntimeTrace(
            route=route,
            role_id=self.role_id or "",
            role_source=self.role_source,
            route_reason=self.route_reason,
            tot_used=bool(self.selected_plan),
            selected_plan=self.selected_plan,
            plan_select_reason=self.plan_select_reason,
            graph_steps=self.graph_steps_used,
            graph_hit_limit=self.graph_hit_limit,
            tool_count=len(self.last_tool_steps),
            refine_used=bool(self.last_refined),
            done_ok=self.last_done_ok,
            node_path_summary=" → ".join(self.last_node_path[:12])
            + (" …" if len(self.last_node_path) > 12 else ""),
            policy_summary=" → ".join(self.last_policy_labels[:6])
            + (" …" if len(self.last_policy_labels) > 6 else ""),
        )

    def chat(self, user_text: str) -> tuple[str, MechanismSnapshot]:
        self.ensure_role_from_user(user_text)
        if self.role is None:
            raise RuntimeError("角色尚未加载")
        self._clear_reflection_state()
        self._clear_graph_state()

        route = analyze_task(user_text)
        self.last_task_route = route

        effective = user_text
        if route.use_tot:
            self._run_tot(user_text)
            effective = (
                f"{user_text}\n\n"
                f"[本轮执行计划（内部比选）]\n{self.selected_plan}"
            )

        final_text = self._run_langgraph(effective)
        final_text = self._maybe_refine(user_text, final_text, route)

        self.last_cot = parse_cot(final_text) if final_text else None
        self.runtime_trace = self._build_trace(route)
        self.runtime_trace.build_lines()

        self.round_count += 1
        if self.turn_history:
            self.turn_history[-1].messages_after = copy.deepcopy(self.messages)
        return final_text, self.snapshot()

    def reset(self) -> MechanismSnapshot:
        snap = super().reset()
        self._clear_graph_state()
        self._thread_id = str(uuid.uuid4())
        return snap

    def reload_role(self, role_id: str) -> MechanismSnapshot:
        snap = super().reload_role(role_id)
        self._clear_graph_state()
        return snap


CommercialAgentSession = LangGraphAgentSession
GraphAgentSession = LangGraphAgentSession
