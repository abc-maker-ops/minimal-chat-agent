# -*- coding: utf-8 -*-
"""reasoning_v4：在 role_setting_v3 上叠加 Prompt 层 CoT 与可选简化 ToT。"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

_LAB = Path(__file__).resolve().parent.parent
_V3 = _LAB / "role_setting_v3"
sys.path.insert(0, str(_LAB / "minimal_chat_v1"))
sys.path.insert(0, str(_V3))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agent_session import MechanismSnapshot  # noqa: E402

from cot_parser import CotSections, parse_cot  # noqa: E402
from message_builder import build_seed_messages  # noqa: E402
from plan_selector import propose_plans, select_plan  # noqa: E402
from role_loader import RoleSpec, load_role  # noqa: E402
from role_router import select_role_id  # noqa: E402


def _load_v3_session_module():
    spec = importlib.util.spec_from_file_location(
        "role_setting_v3_prompt_session",
        _V3 / "prompt_session.py",
    )
    if spec is None or spec.loader is None:
        raise ImportError("无法加载 role_setting_v3/prompt_session.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_v3_session = _load_v3_session_module()
RoleAgentSession = _v3_session.RoleAgentSession
resolve_role_env = _v3_session.resolve_role_env
AUTO_ROLE = _v3_session.AUTO_ROLE


def resolve_tot_enabled() -> bool:
    mode = (os.getenv("REASONING_MODE") or "cot").strip().lower()
    if mode in {"tot", "tree", "plan"}:
        return True
    raw = os.getenv("ENABLE_TOT", "").strip().lower()
    return raw in {"1", "true", "yes"}


class CotAgentSession(RoleAgentSession):
    """v4：v3 选角栈 + Prompt CoT；REASONING_MODE=tot 时简化比选。"""

    def __init__(
        self,
        *,
        role_id: str | None = None,
        include_few_shot: bool = True,
        include_cot: bool = True,
        tot_enabled: bool | None = None,
        force_auto: bool = False,
    ) -> None:
        self.include_cot = include_cot
        self.tot_enabled = resolve_tot_enabled() if tot_enabled is None else tot_enabled
        self.last_cot: CotSections | None = None
        self.last_plans: tuple[str, ...] = ()
        self.selected_plan: str = ""
        self.plan_select_reason: str = ""
        super().__init__(
            role_id=role_id,
            include_few_shot=include_few_shot,
            force_auto=force_auto,
        )

    def _apply_role(self, role_id: str, *, source: str, reason: str = "") -> None:
        self.role = load_role(role_id)
        self.role_id = self.role.id
        self.role_source = source
        self.route_reason = reason
        self.auto_pending = False
        self.messages = build_seed_messages(
            self.role,
            include_few_shot=self.include_few_shot,
            include_cot=self.include_cot,
        )
        self.seed_count = len(self.messages)

    def _run_tot(self, user_text: str) -> None:
        assert self.role is not None
        system = self.role.compose_system(
            include_few_shot=False,
            include_cot=False,
        )
        plans = propose_plans(
            self.client,
            model=self.config.model,
            system=system,
            user_task=user_text,
        )
        idx, reason = select_plan(
            self.client,
            model=self.config.model,
            user_task=user_text,
            plans=plans,
        )
        self.last_plans = tuple(plans)
        self.selected_plan = plans[idx]
        self.plan_select_reason = reason

    def chat(self, user_text: str) -> tuple[str, MechanismSnapshot]:
        self.ensure_role_from_user(user_text)
        if self.role is None:
            raise RuntimeError("角色尚未加载")
        effective = user_text
        self.last_plans = ()
        self.selected_plan = ""
        self.plan_select_reason = ""
        if self.tot_enabled:
            self._run_tot(user_text)
            effective = (
                f"{user_text}\n\n"
                f"[本轮执行计划（ToT 比选后）]\n{self.selected_plan}"
            )
        reply, snap = super().chat(effective)
        self.last_cot = parse_cot(reply)
        return reply, snap

    def reset(self) -> MechanismSnapshot:
        snap = super().reset()
        self.last_cot = None
        self.last_plans = ()
        self.selected_plan = ""
        self.plan_select_reason = ""
        return snap

    def reload_role(self, role_id: str) -> MechanismSnapshot:
        snap = super().reload_role(role_id)
        self.last_cot = None
        self.last_plans = ()
        self.selected_plan = ""
        self.plan_select_reason = ""
        return snap

    def cot_format_ok(self) -> bool:
        return bool(self.last_cot and self.last_cot.ok)
