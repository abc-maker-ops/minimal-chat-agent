# -*- coding: utf-8 -*-
"""role_setting_v3 会话：角色加载、手动/自动选角、固定前缀。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_LAB / "minimal_chat_v1"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agent_session import AgentSession, MechanismSnapshot  # noqa: E402

from message_builder import build_seed_messages  # noqa: E402
from role_loader import RoleSpec, load_role  # noqa: E402
from role_router import select_role_id  # noqa: E402

AUTO_ROLE = "auto"


def resolve_role_env() -> str:
    return (os.getenv("AGENT_ROLE") or "teacher").strip()


class RoleAgentSession(AgentSession):
    """v3：按角色文件注入 system；支持 AGENT_ROLE=auto 首句路由。"""

    def __init__(
        self,
        *,
        role_id: str | None = None,
        include_few_shot: bool = True,
        force_auto: bool = False,
    ) -> None:
        super().__init__()
        self.include_few_shot = include_few_shot
        self.force_auto = force_auto
        env_role = resolve_role_env() if role_id is None else role_id.strip()
        self.requested_role = env_role
        self.auto_pending = force_auto or env_role.lower() == AUTO_ROLE
        self.role: RoleSpec | None = None
        self.role_id: str | None = None
        self.role_source: str = "pending" if self.auto_pending else "manual"
        self.route_reason: str = ""
        self.seed_count = 0

        if not self.auto_pending:
            self._apply_role(env_role, source="manual")

    def _apply_role(self, role_id: str, *, source: str, reason: str = "") -> None:
        self.role = load_role(role_id)
        self.role_id = self.role.id
        self.role_source = source
        self.route_reason = reason
        self.auto_pending = False
        self.messages = build_seed_messages(self.role, include_few_shot=self.include_few_shot)
        self.seed_count = len(self.messages)

    def ensure_role_from_user(self, user_text: str) -> None:
        if not self.auto_pending:
            return
        rid, reason = select_role_id(user_text)
        self._apply_role(rid, source="auto", reason=reason)

    def chat(self, user_text: str) -> tuple[str, MechanismSnapshot]:
        self.ensure_role_from_user(user_text)
        if self.role is None:
            raise RuntimeError("角色尚未加载")
        return super().chat(user_text)

    def reset(self) -> MechanismSnapshot:
        super().reset()
        if self.force_auto or self.requested_role.lower() == AUTO_ROLE:
            self.auto_pending = True
            self.role = None
            self.role_id = None
            self.role_source = "pending"
            self.route_reason = ""
            self.seed_count = 0
        else:
            assert self.role_id is not None
            self._apply_role(self.role_id, source="manual")
        return self.snapshot()

    def reload_role(self, role_id: str) -> MechanismSnapshot:
        """会话边界换角：重建固定前缀，清空多轮。"""
        self.requested_role = role_id
        self.force_auto = role_id.lower() == AUTO_ROLE
        self.auto_pending = self.force_auto
        super().reset()
        if not self.auto_pending:
            self._apply_role(role_id, source="manual")
        else:
            self.role = None
            self.role_id = None
            self.role_source = "pending"
            self.route_reason = ""
            self.seed_count = 0
        return self.snapshot()

    def role_label(self) -> str:
        if self.auto_pending:
            return "（待首句自动选角）"
        if self.role is None:
            return "—"
        return f"{self.role.display_name} ({self.role.id} v{self.role.version})"

    def role_source_label(self) -> str:
        if self.role_source == "manual":
            return "指定"
        if self.role_source == "auto":
            extra = f" · {self.route_reason}" if self.route_reason else ""
            return f"自动{extra}"
        return "待路由"
