# -*- coding: utf-8 -*-
"""reflection_v5：v4 思维链/思维树 + Reflection 质检（自洽、批评、精炼）。"""
from __future__ import annotations

import copy
import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

_LAB = Path(__file__).resolve().parent.parent
_V4 = _LAB / "reasoning_v4"
sys.path.insert(0, str(_LAB / "minimal_chat_v1"))
sys.path.insert(0, str(_LAB / "role_setting_v3"))
sys.path.insert(0, str(_V4))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agent_session import MechanismSnapshot, TurnRecord, TurnUsage  # noqa: E402
from api_resilience import create_chat_completion  # noqa: E402

_cv_spec = importlib.util.spec_from_file_location(
    "reflection_v5_consistency_voter",
    Path(__file__).resolve().parent / "consistency_voter.py",
)
if _cv_spec is None or _cv_spec.loader is None:
    raise ImportError("无法加载 reflection_v5/consistency_voter.py")
_cv_mod = importlib.util.module_from_spec(_cv_spec)
sys.modules["reflection_v5_consistency_voter"] = _cv_mod
_cv_spec.loader.exec_module(_cv_mod)
ConsistencyResult = _cv_mod.ConsistencyResult
resolve_consistency_samples = _cv_mod.resolve_consistency_samples
resolve_consistency_threshold = _cv_mod.resolve_consistency_threshold
vote_conclusions = _cv_mod.vote_conclusions
from cot_parser import CotSections, parse_cot  # noqa: E402
from refine_loop import resolve_max_refine_rounds  # noqa: E402

_v4_spec = importlib.util.spec_from_file_location("reasoning_v4_prompt_session", _V4 / "prompt_session.py")
if _v4_spec is None or _v4_spec.loader is None:
    raise ImportError("无法加载 reasoning_v4/prompt_session.py")
_v4_mod = importlib.util.module_from_spec(_v4_spec)
_v4_spec.loader.exec_module(_v4_mod)
CotAgentSession = _v4_mod.CotAgentSession
resolve_tot_enabled = _v4_mod.resolve_tot_enabled


def resolve_quality_mode(explicit: str | None = None) -> str:
    raw = (explicit or os.getenv("QUALITY_MODE") or "off").strip().lower()
    if raw in {"consistency", "self_consistency", "sc", "self-consistency"}:
        return "consistency"
    if raw in {"refine", "critique", "reflection"}:
        return "refine"
    if raw in {"all", "both", "full"}:
        return "all"
    return "off"


class ReflectionAgentSession(CotAgentSession):
    """v5 Reflection：在 CotAgentSession 上叠加质检旁路。"""

    def __init__(
        self,
        *,
        role_id: str | None = None,
        include_few_shot: bool = True,
        include_cot: bool = True,
        tot_enabled: bool | None = None,
        force_auto: bool = False,
        quality_mode: str | None = None,
    ) -> None:
        self.quality_mode = quality_mode or resolve_quality_mode()
        tot = resolve_tot_enabled() if tot_enabled is None else tot_enabled
        super().__init__(
            role_id=role_id,
            include_few_shot=include_few_shot,
            include_cot=include_cot,
            tot_enabled=tot,
            force_auto=force_auto,
        )
        self.last_consistency: ConsistencyResult | None = None
        self.consensus_conclusion: str = ""
        self.agreement_rate: float = 0.0
        self.consistency_below_threshold: bool = False
        self.last_draft: str = ""
        self.last_critique: str = ""
        self.last_refined: str = ""

    def _clear_reflection_state(self) -> None:
        self.last_consistency = None
        self.consensus_conclusion = ""
        self.agreement_rate = 0.0
        self.consistency_below_threshold = False
        self.last_draft = ""
        self.last_critique = ""
        self.last_refined = ""

    def _record_api_call(
        self,
        body: dict[str, Any],
        response: Any,
        *,
        note: str = "",
    ) -> TurnUsage | None:
        """旁路 API 调用写入 turn_history，供机制查看器「API 原始报文」展示。"""
        req: dict[str, Any] = {
            "method": "POST",
            "path": "/chat/completions",
            "base_url": self.config.base_url,
            "body": copy.deepcopy(body),
        }
        if note:
            req["note"] = note
        self._last_request = req
        self._last_response = self._serialize_api_response(response)

        usage = getattr(response, "usage", None)
        turn_usage = None
        if usage is not None:
            turn_usage = TurnUsage(
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
            )
            self._last_usage = turn_usage
            self.cumulative_prompt += usage.prompt_tokens
            self.cumulative_completion += usage.completion_tokens
            self.cumulative_total += usage.total_tokens

        api_round = len(self.turn_history) + 1
        self.turn_history.append(
            TurnRecord(
                round=api_round,
                request=copy.deepcopy(req),
                response=copy.deepcopy(self._last_response),
                messages_after=copy.deepcopy(self.messages),
                usage=turn_usage,
            )
        )
        return turn_usage

    def _api_completion(
        self,
        messages: list[dict],
        *,
        temperature: float | None = None,
        note: str = "",
    ) -> tuple[str, TurnUsage | None]:
        body: dict[str, Any] = {
            "model": self.config.model,
            "messages": copy.deepcopy(messages),
        }
        temp = temperature if temperature is not None else self.config.temperature
        if temp is not None:
            body["temperature"] = temp
        if self.config.max_tokens is not None:
            body["max_tokens"] = self.config.max_tokens
        response = create_chat_completion(self.client, **body)
        text = response.choices[0].message.content or ""
        turn_usage = self._record_api_call(body, response, note=note)
        return text, turn_usage

    def _ephemeral_completion(
        self,
        user_content: str,
        *,
        temperature: float | None = None,
        note: str = "draft",
    ) -> tuple[str, TurnUsage | None]:
        msgs = list(self.messages) + [{"role": "user", "content": user_content}]
        return self._api_completion(msgs, temperature=temperature, note=note)

    def _run_self_critic_recorded(
        self, system: str, user_task: str, draft: str
    ) -> str:
        user = (
            f"用户任务：{user_task}\n\n"
            f"待批评的助手回复：\n{draft}\n\n"
            "请列出该回复的问题（漏项、逻辑、格式、与角色冲突等），"
            "用条目列表输出，不要给出修订稿。"
        )
        msgs = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        text, _ = self._api_completion(msgs, note="self_critic")
        return text

    def _run_refine_recorded(
        self, system: str, user_task: str, draft: str, critique: str
    ) -> str:
        user = (
            f"用户任务：{user_task}\n\n"
            f"初稿：\n{draft}\n\n"
            f"批评意见：\n{critique}\n\n"
            "请根据批评修订，输出须含且仅含 ## 推理 与 ## 结论 两段。"
        )
        msgs = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        text, _ = self._api_completion(msgs, note="refine")
        return text

    def _commit_assistant_turn(
        self, user_text: str, assistant_text: str, usage: TurnUsage | None = None
    ) -> MechanismSnapshot:
        del usage
        self.messages.append({"role": "user", "content": user_text})
        self.messages.append({"role": "assistant", "content": assistant_text})
        self.round_count += 1
        if self.turn_history:
            self.turn_history[-1].messages_after = copy.deepcopy(self.messages)
        return self.snapshot()

    def _prepare_user_message(self, user_text: str) -> str:
        self.last_plans = ()
        self.selected_plan = ""
        self.plan_select_reason = ""
        if self.tot_enabled:
            self._run_tot(user_text)
            return (
                f"{user_text}\n\n"
                f"[本轮执行计划（ToT 比选后）]\n{self.selected_plan}"
            )
        return user_text

    def _generate_draft(self, user_text: str) -> tuple[str, TurnUsage | None]:
        effective = self._prepare_user_message(user_text)
        return self._ephemeral_completion(effective)

    def _run_consistency(self, user_text: str) -> tuple[str, MechanismSnapshot]:
        samples = resolve_consistency_samples()
        temp = _optional_float("CONSISTENCY_TEMPERATURE") or 0.7
        parsed_list: list[CotSections] = []
        conclusions: list[str] = []
        for _ in range(samples):
            raw, _ = self._ephemeral_completion(
                user_text, temperature=temp, note="consistency"
            )
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
        threshold = resolve_consistency_threshold()
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
        self.consistency_below_threshold = rate < threshold
        chosen_raw = chosen.raw if chosen else winner
        self.last_cot = parse_cot(chosen_raw)
        snap = self._commit_assistant_turn(user_text, chosen_raw)
        return chosen_raw, snap

    def _run_critique_refine(self, user_text: str) -> tuple[str, MechanismSnapshot]:
        assert self.role is not None
        system = self.role.compose_system(
            include_few_shot=self.include_few_shot,
            include_cot=self.include_cot,
        )
        draft, _ = self._generate_draft(user_text)
        self.last_draft = draft
        critique = self._run_self_critic_recorded(system, user_text, draft)
        self.last_critique = critique
        refined = self._run_refine_recorded(system, user_text, draft, critique)
        self.last_refined = refined
        self.last_cot = parse_cot(refined)
        max_rounds = resolve_max_refine_rounds()
        if max_rounds > 1 and not self.last_cot.ok:
            critique2 = self._run_self_critic_recorded(system, user_text, refined)
            self.last_critique = critique2
            refined = self._run_refine_recorded(
                system, user_text, refined, critique2
            )
            self.last_refined = refined
            self.last_cot = parse_cot(refined)
        snap = self._commit_assistant_turn(user_text, refined)
        return refined, snap

    def chat(self, user_text: str) -> tuple[str, MechanismSnapshot]:
        self.ensure_role_from_user(user_text)
        if self.role is None:
            raise RuntimeError("角色尚未加载")
        self._clear_reflection_state()
        mode = self.quality_mode
        if mode == "consistency":
            return self._run_consistency(user_text)
        if mode in {"refine", "all"}:
            return self._run_critique_refine(user_text)
        reply, snap = super().chat(user_text)
        self.last_cot = parse_cot(reply)
        return reply, snap

    def reset(self) -> MechanismSnapshot:
        snap = super().reset()
        self._clear_reflection_state()
        return snap

    def reload_role(self, role_id: str) -> MechanismSnapshot:
        snap = super().reload_role(role_id)
        self._clear_reflection_state()
        return snap


def _optional_float(name: str) -> float | None:
    raw = os.getenv(name, "").strip()
    return float(raw) if raw else None
