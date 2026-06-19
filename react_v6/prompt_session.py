# -*- coding: utf-8 -*-
"""react_v6：一体化运行机制 + ReAct + calculator（第 07 篇）。"""
from __future__ import annotations

import copy
import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

_LAB = Path(__file__).resolve().parent.parent
_RV5 = _LAB / "reflection_v5"
sys.path.insert(0, str(_LAB / "minimal_chat_v1"))
sys.path.insert(0, str(_LAB / "role_setting_v3"))
sys.path.insert(0, str(_LAB / "reasoning_v4"))
sys.path.insert(0, str(_RV5))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agent_session import MechanismSnapshot, TurnUsage  # noqa: E402
from api_resilience import create_chat_completion  # noqa: E402
from cot_parser import parse_cot  # noqa: E402
from runtime_trace import RuntimeTrace  # noqa: E402
from task_router import TaskRoute, analyze_task  # noqa: E402
from tool_registry import TOOL_SCHEMAS, run_tool  # noqa: E402
from tool_steps import ToolStep  # noqa: E402

_rv5_spec = importlib.util.spec_from_file_location(
    "reflection_v5_prompt_session", _RV5 / "prompt_session.py"
)
if _rv5_spec is None or _rv5_spec.loader is None:
    raise ImportError("无法加载 reflection_v5/prompt_session.py")
_rv5_mod = importlib.util.module_from_spec(_rv5_spec)
_rv5_spec.loader.exec_module(_rv5_mod)
ReflectionAgentSession = _rv5_mod.ReflectionAgentSession


def resolve_max_react_steps() -> int:
    raw = (os.getenv("MAX_REACT_STEPS") or "8").strip()
    try:
        n = int(raw)
    except ValueError:
        n = 8
    return max(1, min(n, 16))


def _assistant_dict_from_message(msg: Any) -> dict[str, Any]:
    content = msg.content
    if content is None:
        content = ""
    out: dict[str, Any] = {"role": "assistant", "content": content}
    tool_calls = getattr(msg, "tool_calls", None) or []
    if tool_calls:
        serialized: list[dict[str, Any]] = []
        for tc in tool_calls:
            fn = tc.function
            serialized.append(
                {
                    "id": tc.id,
                    "type": getattr(tc, "type", None) or "function",
                    "function": {
                        "name": fn.name,
                        "arguments": fn.arguments or "{}",
                    },
                }
            )
        out["tool_calls"] = serialized
    return out


class CommercialAgentSession(ReflectionAgentSession):
    """v6：商用 Agent 一体化运行机制 — 用户只发任务，程序自动叠层。"""

    def __init__(self, *, role_id: str | None = None) -> None:
        super().__init__(
            role_id=role_id,
            include_few_shot=True,
            include_cot=True,
            tot_enabled=False,
            force_auto=True,
            quality_mode="off",
        )
        self.last_tool_steps: tuple[ToolStep, ...] = ()
        self.react_steps_used: int = 0
        self.react_hit_limit: bool = False
        self.last_task_route: TaskRoute | None = None
        self.runtime_trace: RuntimeTrace | None = None

    def _clear_react_state(self) -> None:
        self.last_tool_steps = ()
        self.react_steps_used = 0
        self.react_hit_limit = False
        self.last_task_route = None
        self.runtime_trace = None

    def _completion_with_tools(
        self,
        *,
        note: str = "react",
    ) -> tuple[Any, TurnUsage | None]:
        body: dict[str, Any] = {
            "model": self.config.model,
            "messages": copy.deepcopy(self.messages),
            "tools": copy.deepcopy(TOOL_SCHEMAS),
            "tool_choice": "auto",
        }
        if self.config.temperature is not None:
            body["temperature"] = self.config.temperature
        if self.config.max_tokens is not None:
            body["max_tokens"] = self.config.max_tokens
        response = create_chat_completion(self.client, **body)
        turn_usage = self._record_api_call(body, response, note=note)
        return response, turn_usage

    def _run_react(self, user_text: str) -> str:
        self.messages.append({"role": "user", "content": user_text})
        steps: list[ToolStep] = []
        max_steps = resolve_max_react_steps()
        final_text = ""

        for i in range(max_steps):
            response, _ = self._completion_with_tools(note=f"react_{i + 1}")
            msg = response.choices[0].message
            self.messages.append(_assistant_dict_from_message(msg))
            tool_calls = getattr(msg, "tool_calls", None) or []
            if not tool_calls:
                final_text = (msg.content or "").strip()
                self.react_steps_used = i + 1
                break

            for tc in tool_calls:
                fn = tc.function
                args = fn.arguments or "{}"
                observation = run_tool(fn.name, args)
                ok = not observation.startswith("错误：")
                steps.append(
                    ToolStep(
                        step=len(steps) + 1,
                        tool_name=fn.name,
                        arguments=args,
                        observation=observation,
                        ok=ok,
                    )
                )
                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": observation,
                    }
                )
        else:
            self.react_hit_limit = True
            self.react_steps_used = max_steps
            final_text = (
                f"已达 ReAct 步数上限（MAX_REACT_STEPS={max_steps}），"
                "请缩小任务或提高上限。"
            )

        self.last_tool_steps = tuple(steps)
        return final_text

    def _replace_final_assistant(self, text: str) -> None:
        for i in range(len(self.messages) - 1, -1, -1):
            msg = self.messages[i]
            if msg.get("role") == "assistant" and not msg.get("tool_calls"):
                msg["content"] = text
                return

    def _maybe_refine(self, user_text: str, draft: str, route: TaskRoute) -> str:
        if not route.use_refine or not draft or draft.startswith("已达 ReAct"):
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
            react_steps=self.react_steps_used,
            react_hit_limit=self.react_hit_limit,
            tool_count=len(self.last_tool_steps),
            refine_used=bool(self.last_refined),
        )

    def chat(self, user_text: str) -> tuple[str, MechanismSnapshot]:
        self.ensure_role_from_user(user_text)
        if self.role is None:
            raise RuntimeError("角色尚未加载")
        self._clear_reflection_state()
        self._clear_react_state()

        route = analyze_task(user_text)
        self.last_task_route = route

        effective = user_text
        if route.use_tot:
            self._run_tot(user_text)
            effective = (
                f"{user_text}\n\n"
                f"[本轮执行计划（内部比选）]\n{self.selected_plan}"
            )

        final_text = self._run_react(effective)
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
        self._clear_react_state()
        return snap

    def reload_role(self, role_id: str) -> MechanismSnapshot:
        snap = super().reload_role(role_id)
        self._clear_react_state()
        return snap


# 机制查看器与测试沿用旧名
ReactAgentSession = CommercialAgentSession
