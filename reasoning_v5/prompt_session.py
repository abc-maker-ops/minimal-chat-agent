# -*- coding: utf-8 -*-
"""reasoning_v5：对标厂商落地思维链 / 思维树 / 思维图（在 v4 上扩展）。"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

_LAB = Path(__file__).resolve().parent.parent
_V4 = _LAB / "reasoning_v4"
sys.path.insert(0, str(_LAB / "minimal_chat_v1"))
sys.path.insert(0, str(_LAB / "role_setting_v3"))
sys.path.insert(0, str(_V4))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agent_session import MechanismSnapshot, TurnUsage  # noqa: E402
from api_resilience import create_chat_completion  # noqa: E402

from consistency_voter import (  # noqa: E402
    ConsistencyResult,
    resolve_consistency_samples,
    vote_conclusions,
)
from cot_parser import CotSections, parse_cot  # noqa: E402
from graph_runner import GraphBranch, GraphRunResult, run_graph_branches  # noqa: E402

_v4_spec = importlib.util.spec_from_file_location("reasoning_v4_prompt_session", _V4 / "prompt_session.py")
if _v4_spec is None or _v4_spec.loader is None:
    raise ImportError("无法加载 reasoning_v4/prompt_session.py")
_v4_mod = importlib.util.module_from_spec(_v4_spec)
_v4_spec.loader.exec_module(_v4_mod)
CotAgentSession = _v4_mod.CotAgentSession
resolve_tot_enabled = _v4_mod.resolve_tot_enabled


def resolve_reasoning_mode() -> str:
    mode = (os.getenv("REASONING_MODE") or "cot").strip().lower()
    if mode in {"tot", "tree", "plan"}:
        return "tot"
    if mode in {"consistency", "self_consistency", "sc", "self-consistency"}:
        return "consistency"
    if mode in {"graph", "got", "parallel", "fanout"}:
        return "graph"
    return "cot"


class ReasoningV5Session(CotAgentSession):
    """v5：v4 + 自洽性（CoT 产品增强）+ 并行汇总（GoT 产品简化）。"""

    def __init__(
        self,
        *,
        role_id: str | None = None,
        include_few_shot: bool = True,
        include_cot: bool = True,
        reasoning_mode: str | None = None,
        tot_enabled: bool | None = None,
        force_auto: bool = False,
    ) -> None:
        mode = reasoning_mode or resolve_reasoning_mode()
        self.reasoning_mode = mode
        tot = mode == "tot" if tot_enabled is None else tot_enabled
        super().__init__(
            role_id=role_id,
            include_few_shot=include_few_shot,
            include_cot=include_cot,
            tot_enabled=tot,
            force_auto=force_auto,
        )
        self.last_consistency: ConsistencyResult | None = None
        self.last_graph_branches: tuple[GraphBranch, ...] = ()
        self.consensus_conclusion: str = ""
        self.agreement_rate: float = 0.0

    def _clear_v5_state(self) -> None:
        self.last_consistency = None
        self.last_graph_branches = ()
        self.consensus_conclusion = ""
        self.agreement_rate = 0.0

    def _ephemeral_completion(
        self,
        user_content: str,
        *,
        temperature: float | None = None,
    ) -> tuple[str, TurnUsage | None]:
        msgs = list(self.messages) + [{"role": "user", "content": user_content}]
        body: dict = {"model": self.config.model, "messages": msgs}
        temp = temperature if temperature is not None else self.config.temperature
        if temp is not None:
            body["temperature"] = temp
        if self.config.max_tokens is not None:
            body["max_tokens"] = self.config.max_tokens
        response = create_chat_completion(self.client, **body)
        text = response.choices[0].message.content or ""
        usage = getattr(response, "usage", None)
        turn_usage = None
        if usage is not None:
            turn_usage = TurnUsage(
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
            )
        return text, turn_usage

    def _commit_assistant_turn(self, user_text: str, assistant_text: str, usage: TurnUsage | None) -> MechanismSnapshot:
        self.messages.append({"role": "user", "content": user_text})
        self.messages.append({"role": "assistant", "content": assistant_text})
        self._last_usage = usage
        if usage is not None:
            self.cumulative_prompt += usage.prompt_tokens
            self.cumulative_completion += usage.completion_tokens
            self.cumulative_total += usage.total_tokens
        self.round_count += 1
        return self.snapshot()

    def _run_consistency(self, user_text: str) -> tuple[str, MechanismSnapshot]:
        samples = resolve_consistency_samples()
        temp = _optional_float("CONSISTENCY_TEMPERATURE") or 0.7
        parsed_list: list[CotSections] = []
        conclusions: list[str] = []
        last_usage: TurnUsage | None = None
        for _ in range(samples):
            raw, usage = self._ephemeral_completion(user_text, temperature=temp)
            last_usage = usage
            cot = parse_cot(raw)
            parsed_list.append(cot)
            conclusions.append(cot.conclusion or raw.strip())
        winner, winner_count, rate = vote_conclusions(conclusions)
        chosen: CotSections | None = None
        for cot in parsed_list:
            if (cot.conclusion or "").strip() == winner:
                chosen = cot
                break
        if chosen is None and parsed_list:
            chosen = parsed_list[0]
        self.last_consistency = ConsistencyResult(
            samples=tuple(parsed_list),
            conclusions=tuple(conclusions),
            winner=winner,
            winner_count=winner_count,
            agreement_rate=rate,
            chosen=chosen,
        )
        self.consensus_conclusion = winner
        self.agreement_rate = rate
        chosen_raw = chosen.raw if chosen else winner
        self.last_cot = parse_cot(chosen_raw)
        snap = self._commit_assistant_turn(user_text, chosen_raw, last_usage)
        return chosen_raw, snap

    def _run_graph(self, user_text: str) -> tuple[str, MechanismSnapshot]:
        assert self.role is not None
        system = self.role.compose_system(
            include_few_shot=False,
            include_cot=False,
        )
        graph: GraphRunResult = run_graph_branches(
            self.client,
            model=self.config.model,
            system=system,
            user_task=user_text,
        )
        self.last_graph_branches = graph.branches
        reply, snap = super().chat(graph.merged_user)
        self.last_cot = parse_cot(reply)
        return reply, snap

    def chat(self, user_text: str) -> tuple[str, MechanismSnapshot]:
        self.ensure_role_from_user(user_text)
        if self.role is None:
            raise RuntimeError("角色尚未加载")
        self._clear_v5_state()
        self.last_plans = ()
        self.selected_plan = ""
        self.plan_select_reason = ""
        if self.reasoning_mode == "consistency":
            return self._run_consistency(user_text)
        if self.reasoning_mode == "graph":
            return self._run_graph(user_text)
        reply, snap = super().chat(user_text)
        self.last_cot = parse_cot(reply)
        return reply, snap

    def reset(self) -> MechanismSnapshot:
        snap = super().reset()
        self._clear_v5_state()
        return snap

    def reload_role(self, role_id: str) -> MechanismSnapshot:
        snap = super().reload_role(role_id)
        self._clear_v5_state()
        return snap


def _optional_float(name: str) -> float | None:
    raw = os.getenv(name, "").strip()
    return float(raw) if raw else None
