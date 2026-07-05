# -*- coding: utf-8 -*-
"""react_v8：v7 读写/done + tool_choice / parallel / forced tool（第 09 篇）。"""
from __future__ import annotations

import copy
import importlib.util
import os
import re
import sys
from pathlib import Path
from typing import Any

_LAB = Path(__file__).resolve().parent.parent
_RV5 = _LAB / "reflection_v5"
_V8 = Path(__file__).resolve().parent
sys.path.insert(0, str(_LAB / "minimal_chat_v1"))
sys.path.insert(0, str(_LAB / "role_setting_v3"))
sys.path.insert(0, str(_LAB / "reasoning_v4"))
sys.path.insert(0, str(_RV5))
sys.path.insert(0, str(_V8))


def _import_v8_module(short: str):
    qual = f"react_v8_{short}"
    if qual in sys.modules:
        return sys.modules[qual]
    path = _V8 / f"{short}.py"
    spec = importlib.util.spec_from_file_location(qual, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载 react_v8/{short}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[qual] = mod
    v8s = str(_V8)
    if sys.path[0] != v8s:
        sys.path.insert(0, v8s)
    spec.loader.exec_module(mod)
    return mod


from agent_session import MechanismSnapshot, TurnUsage  # noqa: E402
from api_resilience import create_chat_completion  # noqa: E402
from cot_parser import parse_cot  # noqa: E402

_runtime_trace = _import_v8_module("runtime_trace")
RuntimeTrace = _runtime_trace.RuntimeTrace
_task_router = _import_v8_module("task_router")
TaskRoute = _task_router.TaskRoute
analyze_task = _task_router.analyze_task
_tool_registry = _import_v8_module("tool_registry")
TOOL_SCHEMAS = _tool_registry.TOOL_SCHEMAS
run_tool = _tool_registry.run_tool
_tool_steps = _import_v8_module("tool_steps")
ToolStep = _tool_steps.ToolStep
_tool_policy = _import_v8_module("tool_policy")
ReactContext = _tool_policy.ReactContext
ToolPolicy = _tool_policy.ToolPolicy
resolve_tool_policy = _tool_policy.resolve_tool_policy
should_force_done_after_text_exit = _tool_policy.should_force_done_after_text_exit
_parallel = _import_v8_module("parallel_runner")
execute_tool_calls = _parallel.execute_tool_calls
_workspace = _import_v8_module("workspace")
workspace_root = _workspace.workspace_root

_rv5_spec = importlib.util.spec_from_file_location(
    "reflection_v5_prompt_session", _RV5 / "prompt_session.py"
)
if _rv5_spec is None or _rv5_spec.loader is None:
    raise ImportError("无法加载 reflection_v5/prompt_session.py")
_rv5_mod = importlib.util.module_from_spec(_rv5_spec)
_rv5_spec.loader.exec_module(_rv5_mod)
ReflectionAgentSession = _rv5_mod.ReflectionAgentSession


def resolve_max_react_steps() -> int:
    raw = (os.getenv("MAX_REACT_STEPS") or "10").strip()
    try:
        n = int(raw)
    except ValueError:
        n = 10
    return max(1, min(n, 24))


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


def _observation_ok(observation: str, tool_name: str) -> bool:
    if observation.startswith("错误："):
        return False
    if tool_name == "done":
        try:
            import json

            data = json.loads(observation)
            return bool(data.get("ok"))
        except json.JSONDecodeError:
            return False
    return True


def _user_requires_done(user_text: str) -> bool:
    return bool(re.search(r"\bdone\b|验收|required_headings|required_keys", user_text, re.I))


class ToolEngineeredAgentSession(ReflectionAgentSession):
    """v8：在 v7 工具表上增加 tool_choice、parallel 与 forced done。"""

    AGENT_GENERATION = 8

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
        self.last_done_ok: bool | None = None
        self.last_tool_policies: tuple[str, ...] = ()
        self.parallel_batch_count: int = 0
        self.workspace_path = workspace_root()

    def _clear_react_state(self) -> None:
        self.last_tool_steps = ()
        self.react_steps_used = 0
        self.react_hit_limit = False
        self.last_task_route = None
        self.runtime_trace = None
        self.last_done_ok = None
        self.last_tool_policies = ()
        self.parallel_batch_count = 0

    def _completion_with_tools(
        self,
        *,
        note: str = "react",
        policy: ToolPolicy | None = None,
    ) -> tuple[Any, TurnUsage | None]:
        pol = policy or resolve_tool_policy(ReactContext(0, False, None))
        body: dict[str, Any] = {
            "model": self.config.model,
            "messages": copy.deepcopy(self.messages),
            "tools": copy.deepcopy(TOOL_SCHEMAS),
            "tool_choice": pol.tool_choice,
        }
        if not pol.parallel_tool_calls:
            body["parallel_tool_calls"] = False
        if self.config.temperature is not None:
            body["temperature"] = self.config.temperature
        if self.config.max_tokens is not None:
            body["max_tokens"] = self.config.max_tokens
        response = create_chat_completion(self.client, **body)
        turn_usage = self._record_api_call(body, response, note=note)
        return response, turn_usage

    def _react_context(
        self,
        *,
        react_round: int,
        has_written: bool,
        user_text: str,
    ) -> ReactContext:
        return ReactContext(
            react_round=react_round,
            has_written_output=has_written,
            done_ok=self.last_done_ok,
            user_requires_done=_user_requires_done(user_text),
        )

    def _process_tool_calls(
        self,
        tool_calls: list[Any],
        *,
        policy: ToolPolicy,
        react_round: int,
        steps: list[ToolStep],
        has_written: bool,
    ) -> bool:
        """执行 tool_calls 并写入 messages；返回 has_written 是否更新。"""
        batch = execute_tool_calls(
            tool_calls,
            run_tool,
            _observation_ok,
            parallel=policy.client_parallel,
            react_round=react_round,
            start_step=len(steps) + 1,
        )
        if batch and batch[0][4] is not None:
            self.parallel_batch_count += 1

        for tc, observation, ok, step_no, group in batch:
            fn = tc.function
            if fn.name == "done":
                self.last_done_ok = ok
            if fn.name == "write_text" and ok:
                has_written = True
            steps.append(
                ToolStep(
                    step=step_no,
                    tool_name=fn.name,
                    arguments=fn.arguments or "{}",
                    observation=observation,
                    ok=ok,
                    react_round=react_round + 1,
                    parallel_group=group,
                )
            )
            self.messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": observation,
                }
            )
        return has_written

    def _run_react(self, user_text: str) -> str:
        self.messages.append({"role": "user", "content": user_text})
        steps: list[ToolStep] = []
        policy_labels: list[str] = []
        max_steps = resolve_max_react_steps()
        final_text = ""
        has_written = False

        for i in range(max_steps):
            ctx = self._react_context(
                react_round=i, has_written=has_written, user_text=user_text
            )
            policy = resolve_tool_policy(ctx)
            policy_labels.append(f"R{i + 1}:{policy.label}")
            response, _ = self._completion_with_tools(
                note=f"react_{i + 1}", policy=policy
            )
            msg = response.choices[0].message
            self.messages.append(_assistant_dict_from_message(msg))
            tool_calls = getattr(msg, "tool_calls", None) or []

            if not tool_calls:
                final_text = (msg.content or "").strip()
                self.react_steps_used = i + 1
                ctx_after = self._react_context(
                    react_round=i, has_written=has_written, user_text=user_text
                )
                if should_force_done_after_text_exit(ctx_after) and i + 1 < max_steps:
                    force_policy = resolve_tool_policy(ctx_after, force_done=True)
                    policy_labels.append(f"R{i + 2}:{force_policy.label}")
                    response, _ = self._completion_with_tools(
                        note=f"react_{i + 2}_force_done", policy=force_policy
                    )
                    msg = response.choices[0].message
                    self.messages.append(_assistant_dict_from_message(msg))
                    tool_calls = getattr(msg, "tool_calls", None) or []
                    if tool_calls:
                        has_written = self._process_tool_calls(
                            tool_calls,
                            policy=force_policy,
                            react_round=i + 1,
                            steps=steps,
                            has_written=has_written,
                        )
                        self.react_steps_used = i + 2
                        continue
                break

            has_written = self._process_tool_calls(
                tool_calls,
                policy=policy,
                react_round=i,
                steps=steps,
                has_written=has_written,
            )
        else:
            self.react_hit_limit = True
            self.react_steps_used = max_steps
            final_text = (
                f"已达 ReAct 步数上限（MAX_REACT_STEPS={max_steps}），"
                "请缩小任务或提高上限。"
            )

        self.last_tool_steps = tuple(steps)
        self.last_tool_policies = tuple(policy_labels)
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
            parallel_batches=self.parallel_batch_count,
            refine_used=bool(self.last_refined),
            done_ok=self.last_done_ok,
            tool_policy_summary=" → ".join(self.last_tool_policies[:6])
            + (" …" if len(self.last_tool_policies) > 6 else ""),
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


DeliveryAgentSession = ToolEngineeredAgentSession
CommercialAgentSession = ToolEngineeredAgentSession
ReactAgentSession = ToolEngineeredAgentSession
