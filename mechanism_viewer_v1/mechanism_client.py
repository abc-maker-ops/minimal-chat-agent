# -*- coding: utf-8 -*-
"""
机制查看器（桌面 tkinter）：左侧对话，右侧机制仪表盘 / messages JSON。
窗口顶部可选择不同 Agent 版本（minimal_chat_v1、system_prompt_v2 等）。
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import threading
import tkinter as tk
import tkinter.font as tkfont
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk
from typing import Any

_LAB_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_LAB_ROOT / "minimal_chat_v1"))
sys.path.insert(0, str(_LAB_ROOT / "system_prompt_v2"))


def _load_lab_module(mod_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(mod_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载 {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


_v2_prompt = _load_lab_module(
    "system_prompt_v2_prompt_session",
    _LAB_ROOT / "system_prompt_v2" / "prompt_session.py",
)
_v3_role_loader = _load_lab_module(
    "role_setting_v3_role_loader",
    _LAB_ROOT / "role_setting_v3" / "role_loader.py",
)
_v3_prompt = _load_lab_module(
    "role_setting_v3_prompt_session",
    _LAB_ROOT / "role_setting_v3" / "prompt_session.py",
)
_v4_prompt = _load_lab_module(
    "reasoning_v4_prompt_session",
    _LAB_ROOT / "reasoning_v4" / "prompt_session.py",
)
_refl_prompt = _load_lab_module(
    "reflection_v5_prompt_session",
    _LAB_ROOT / "reflection_v5" / "prompt_session.py",
)
_react_v7_prompt = _load_lab_module(
    "react_v7_prompt_session",
    _LAB_ROOT / "react_v7" / "prompt_session.py",
)
_react_prompt = _load_lab_module(
    "react_v6_prompt_session",
    _LAB_ROOT / "react_v6" / "prompt_session.py",
)
PromptAgentSession = _v2_prompt.PromptAgentSession
RoleAgentSession = _v3_prompt.RoleAgentSession
CotAgentSession = _v4_prompt.CotAgentSession
ReflectionAgentSession = _refl_prompt.ReflectionAgentSession
CommercialAgentSession = _react_prompt.CommercialAgentSession
DeliveryAgentSession = _react_v7_prompt.DeliveryAgentSession
ReactAgentSession = CommercialAgentSession
list_role_ids = _v3_role_loader.list_role_ids

_v3_root = str(_LAB_ROOT / "role_setting_v3")
while _v3_root in sys.path:
    sys.path.remove(_v3_root)

from agent_session import (  # noqa: E402
    DEFAULT_ZHIPU_BASE_URL,
    AgentSession,
    MechanismSnapshot,
    TurnRecord,
)

# —— 界面配色 ——
C_BG = "#eef2f7"
C_SURFACE = "#ffffff"
C_HEADER = "#1e40af"
C_HEADER_TEXT = "#ffffff"
C_BORDER = "#d8e0ea"
C_TEXT = "#0f172a"
C_MUTED = "#64748b"
C_ACCENT = "#2563eb"
C_ACCENT_HOVER = "#1d4ed8"
C_SUCCESS = "#15803d"
C_SUCCESS_BG = "#dcfce7"
C_WARN = "#b45309"
C_WARN_BG = "#fef3c7"
C_ERROR = "#b91c1c"
C_ERROR_BG = "#fee2e2"
C_USER_BG = "#e8f0fe"
C_ASSISTANT_BG = "#ecfdf5"
C_SYSTEM_BG = "#f1f5f9"
C_STAT_MESSAGES = "#3b82f6"
C_STAT_ROUNDS = "#8b5cf6"
C_STAT_TOKENS = "#06b6d4"


@dataclass(frozen=True)
class AgentVersionSpec:
    id: str
    label: str
    hint: str


AGENT_VERSIONS: tuple[AgentVersionSpec, ...] = (
    AgentVersionSpec(
        "v1_minimal",
        "第02篇 · minimal_chat_v1",
        "仅 user/assistant，无 system、无 Few-shot",
    ),
    AgentVersionSpec(
        "v2_fewshot",
        "第03篇 · system + Few-shot",
        "system.txt + few_shot.json 种子（默认）",
    ),
    AgentVersionSpec(
        "v2_zeroshot",
        "第03篇 · system（Zero-shot）",
        "仅 system，不注入 Few-shot 范例",
    ),
    AgentVersionSpec(
        "v3_fewshot",
        "第04篇 · 角色设定 + Few-shot",
        "YAML 角色库 + AGENT_ROLE 指定选角",
    ),
    AgentVersionSpec(
        "v3_zeroshot",
        "第04篇 · 角色设定（Zero-shot）",
        "YAML 角色库，不注入 Few-shot",
    ),
    AgentVersionSpec(
        "v3_auto",
        "第04篇 · 角色设定 · 自动选角",
        "AGENT_ROLE=auto，首条 user 经 role_router 选角",
    ),
    AgentVersionSpec(
        "v4_cot_fewshot",
        "第05篇 · CoT + Few-shot",
        "Prompt 层 ## 推理 / ## 结论 + CoT Few-shot",
    ),
    AgentVersionSpec(
        "v4_cot_zeroshot",
        "第05篇 · CoT（Zero-shot）",
        "仅 CoT 格式约束，不注入 Few-shot",
    ),
    AgentVersionSpec(
        "v4_tot_fewshot",
        "第05篇 · 简化 ToT + CoT",
        "2～3 计划比选后再 CoT 回复",
    ),
    AgentVersionSpec(
        "v5_cot_fewshot",
        "第06篇 · 思维链（Prompt 层）",
        "同第05篇 Prompt CoT，v5 代码栈",
    ),
    AgentVersionSpec(
        "v5_tot_fewshot",
        "第06篇 · 简化思维树",
        "对标 Orchestrator 计划比选（同 v4 ToT）",
    ),
    AgentVersionSpec(
        "v5_consistency_fewshot",
        "第06篇 · 自洽性",
        "多样本结论投票（Self-Consistency）",
    ),
    AgentVersionSpec(
        "v5_refine_fewshot",
        "第06篇 · 批评与精炼",
        "Self-Refine 式 generate → critique → revise",
    ),
    AgentVersionSpec(
        "v5_tot_refine_fewshot",
        "第06篇 · 思维树 + 批评精炼",
        "计划比较选定后再批评修订",
    ),
    AgentVersionSpec(
        "v6_commercial",
        "第07篇 · 商用 Agent",
        "一体化运行机制：自动选角/比选/质检 + ReAct",
    ),
    AgentVersionSpec(
        "v7_delivery",
        "第08篇 · 结构化交付",
        "文件工具 + Markdown/JSON/XML 交付 + done 机器验收",
    ),
)
VERSION_BY_ID = {v.id: v for v in AGENT_VERSIONS}
LABEL_TO_ID = {v.label: v.id for v in AGENT_VERSIONS}

# mechanism_viewer_vN 只看 agent v1～vN；观测 Tab 随 N 递增，不可跨代
VIEWER_PROFILES: dict[str, dict[str, Any]] = {
    "viewer1": {
        "title": "机制查看器 v1",
        "version_ids": ("v1_minimal",),
        "default_version": "v1_minimal",
        "show_role_tab": False,
        "show_reasoning_tab": False,
        "show_raw_tab": False,
    },
    "viewer2": {
        "title": "机制查看器 v2",
        "version_ids": ("v1_minimal", "v2_fewshot", "v2_zeroshot"),
        "default_version": "v2_fewshot",
        "show_role_tab": False,
        "show_reasoning_tab": False,
        "show_raw_tab": True,
    },
    "viewer3": {
        "title": "机制查看器 v3",
        "version_ids": (
            "v1_minimal",
            "v2_fewshot",
            "v2_zeroshot",
            "v3_fewshot",
            "v3_zeroshot",
            "v3_auto",
        ),
        "default_version": "v3_fewshot",
        "show_role_tab": True,
        "show_reasoning_tab": False,
        "show_raw_tab": True,
    },
    "viewer4": {
        "title": "机制查看器 v4",
        "version_ids": (
            "v1_minimal",
            "v2_fewshot",
            "v2_zeroshot",
            "v3_fewshot",
            "v3_zeroshot",
            "v3_auto",
            "v4_cot_fewshot",
            "v4_cot_zeroshot",
            "v4_tot_fewshot",
        ),
        "default_version": "v4_cot_fewshot",
        "show_role_tab": True,
        "show_reasoning_tab": True,
        "show_raw_tab": True,
    },
    "viewer5": {
        "title": "机制查看器 v5",
        "version_ids": (
            "v1_minimal",
            "v2_fewshot",
            "v2_zeroshot",
            "v3_fewshot",
            "v3_zeroshot",
            "v3_auto",
            "v4_cot_fewshot",
            "v4_cot_zeroshot",
            "v4_tot_fewshot",
            "v5_consistency_fewshot",
            "v5_refine_fewshot",
            "v5_tot_refine_fewshot",
        ),
        "default_version": "v5_refine_fewshot",
        "show_role_tab": True,
        "show_reasoning_tab": True,
        "show_quality_tab": True,
        "show_raw_tab": True,
    },
    "viewer6": {
        "title": "机制查看器 v6",
        "version_ids": ("v6_commercial",),
        "default_version": "v6_commercial",
        "show_role_tab": False,
        "show_reasoning_tab": False,
        "show_quality_tab": False,
        "show_tools_tab": False,
        "show_trajectory_tab": True,
        "show_raw_tab": True,
    },
    "viewer7": {
        "title": "机制查看器 v7",
        "version_ids": ("v7_delivery",),
        "default_version": "v7_delivery",
        "show_role_tab": False,
        "show_reasoning_tab": False,
        "show_quality_tab": False,
        "show_tools_tab": False,
        "show_trajectory_tab": True,
        "show_raw_tab": True,
    },
}


def resolve_viewer_profile(name: str | None) -> str:
    key = (name or os.getenv("MECHANISM_VIEWER_PROFILE") or "viewer1").strip()
    if key == "article4":
        return "viewer3"
    if key not in VIEWER_PROFILES:
        return "viewer1"
    return key


def versions_for_profile(profile: str) -> tuple[AgentVersionSpec, ...]:
    allowed = set(VIEWER_PROFILES[profile]["version_ids"])
    return tuple(v for v in AGENT_VERSIONS if v.id in allowed)


@dataclass
class ViewerMeta:
    version_id: str
    version_label: str
    few_shot: bool | None
    seed_count: int
    keeps_seed_on_reset: bool
    role_id: str | None = None
    role_display_name: str | None = None
    role_version: str | None = None
    role_source: str | None = None
    route_reason: str | None = None


    tot_enabled: bool = False
    include_cot: bool = True


def _is_v3(version_id: str) -> bool:
    return version_id.startswith("v3_")


def _is_v4(version_id: str) -> bool:
    return version_id.startswith("v4_")


def _is_v5(version_id: str) -> bool:
    return version_id.startswith("v5_")


def _is_v6(version_id: str) -> bool:
    return version_id.startswith("v6_")


def _is_v7(version_id: str) -> bool:
    return version_id.startswith("v7_")


def _is_commercial_react_session(
    session: AgentSession | PromptAgentSession | RoleAgentSession | CotAgentSession,
) -> bool:
    return isinstance(session, (CommercialAgentSession, DeliveryAgentSession))


def _is_reasoning(version_id: str) -> bool:
    return (
        _is_v4(version_id)
        or _is_v5(version_id)
        or _is_v6(version_id)
        or _is_v7(version_id)
    )


def _reflection_params_from_version(version_id: str) -> tuple[str, bool]:
    table: dict[str, tuple[str, bool]] = {
        "v5_cot_fewshot": ("off", False),
        "v5_tot_fewshot": ("off", True),
        "v5_consistency_fewshot": ("consistency", False),
        "v5_refine_fewshot": ("refine", False),
        "v5_tot_refine_fewshot": ("refine", True),
    }
    return table.get(version_id, ("off", False))


def _is_role_agent(version_id: str) -> bool:
    return _is_v3(version_id) or _is_reasoning(version_id)


def _role_source_short(session: RoleAgentSession | CotAgentSession) -> str:
    if session.role_source == "manual":
        return "指定"
    if session.role_source == "auto":
        return "自动"
    return "待路由"


def _role_prompt_preview(session: RoleAgentSession | CotAgentSession) -> str:
    if session.messages and session.messages[0].get("role") == "system":
        return str(session.messages[0]["content"])
    if session.role is not None:
        kwargs: dict[str, bool] = {"include_few_shot": session.include_few_shot}
        if hasattr(session, "include_cot"):
            kwargs["include_cot"] = bool(session.include_cot)
        return session.role.compose_system(**kwargs)
    return ""


def _few_shot_seed_hint(
    session: RoleAgentSession | CotAgentSession, meta: ViewerMeta
) -> str:
    if not meta.few_shot:
        return "未开启（Zero-shot 或未配置 few_shot_ref）"
    if meta.seed_count <= 1:
        return "已开启但固定前缀尚无范例对"
    pairs = max(0, (meta.seed_count - 1) // 2)
    ref = None
    if session.role:
        if meta.include_cot and getattr(session.role, "cot_few_shot_ref", None):
            ref = session.role.cot_few_shot_ref
        else:
            ref = session.role.few_shot_ref
    ref_s = f"，来自 {ref}" if ref else ""
    return f"{pairs} 组 user/assistant 范例{ref_s}"


def build_session(
    version_id: str, *, role_choice: str = "teacher"
) -> AgentSession | PromptAgentSession | RoleAgentSession | CotAgentSession:
    if version_id == "v1_minimal":
        return AgentSession()
    if _is_v7(version_id):
        return DeliveryAgentSession()
    if _is_v6(version_id):
        return CommercialAgentSession()
    if _is_v5(version_id):
        quality_mode, tot_enabled = _reflection_params_from_version(version_id)
        return ReflectionAgentSession(
            role_id=role_choice,
            include_few_shot=True,
            include_cot=True,
            quality_mode=quality_mode,
            tot_enabled=tot_enabled,
        )
    if _is_v4(version_id):
        include_few_shot = version_id != "v4_cot_zeroshot"
        tot_enabled = version_id == "v4_tot_fewshot"
        return CotAgentSession(
            role_id=role_choice,
            include_few_shot=include_few_shot,
            include_cot=True,
            tot_enabled=tot_enabled,
        )
    if _is_v3(version_id):
        include_few_shot = version_id != "v3_zeroshot"
        if version_id == "v3_auto" or role_choice == "auto":
            return RoleAgentSession(include_few_shot=include_few_shot, force_auto=True)
        return RoleAgentSession(
            role_id=role_choice,
            include_few_shot=include_few_shot,
        )
    include_few_shot = version_id == "v2_fewshot"
    return PromptAgentSession(include_few_shot=include_few_shot)


def resolve_default_version(
    explicit: str | None = None, *, profile: str = "viewer1"
) -> str:
    cfg = VIEWER_PROFILES.get(profile, VIEWER_PROFILES["viewer1"])
    fallback = str(cfg["default_version"])
    vid = (explicit or os.getenv("MECHANISM_AGENT_VERSION") or fallback).strip()
    allowed = set(cfg["version_ids"])
    if vid not in VERSION_BY_ID or vid not in allowed:
        return fallback
    return vid


def make_viewer_meta(
    version_id: str,
    session: AgentSession | PromptAgentSession | RoleAgentSession | CotAgentSession,
) -> ViewerMeta:
    spec = VERSION_BY_ID[version_id]
    if version_id == "v1_minimal":
        return ViewerMeta(
            version_id=version_id,
            version_label=spec.label,
            few_shot=None,
            seed_count=0,
            keeps_seed_on_reset=False,
        )
    if (_is_v6(version_id) or _is_v7(version_id)) and _is_commercial_react_session(
        session
    ):
        role = session.role
        return ViewerMeta(
            version_id=version_id,
            version_label=spec.label,
            few_shot=True,
            seed_count=session.seed_count,
            keeps_seed_on_reset=True,
            role_id=session.role_id,
            role_display_name=role.display_name if role else None,
            role_version=role.version if role else None,
            role_source=_role_source_short(session),
            route_reason=session.route_reason or None,
            tot_enabled=False,
            include_cot=True,
        )
    if _is_v5(version_id) and isinstance(session, ReflectionAgentSession):
        role = session.role
        return ViewerMeta(
            version_id=version_id,
            version_label=spec.label,
            few_shot=True,
            seed_count=session.seed_count,
            keeps_seed_on_reset=True,
            role_id=session.role_id,
            role_display_name=role.display_name if role else None,
            role_version=role.version if role else None,
            role_source=_role_source_short(session),
            route_reason=session.route_reason or None,
            tot_enabled=session.tot_enabled,
            include_cot=session.include_cot,
        )
    if _is_v4(version_id) and isinstance(session, CotAgentSession):
        few_shot = version_id != "v4_cot_zeroshot"
        role = session.role
        return ViewerMeta(
            version_id=version_id,
            version_label=spec.label,
            few_shot=few_shot,
            seed_count=session.seed_count,
            keeps_seed_on_reset=True,
            role_id=session.role_id,
            role_display_name=role.display_name if role else None,
            role_version=role.version if role else None,
            role_source=_role_source_short(session),
            route_reason=session.route_reason or None,
            tot_enabled=session.tot_enabled,
            include_cot=session.include_cot,
        )
    if _is_v3(version_id) and isinstance(session, RoleAgentSession):
        few_shot = version_id != "v3_zeroshot"
        role = session.role
        return ViewerMeta(
            version_id=version_id,
            version_label=spec.label,
            few_shot=few_shot,
            seed_count=session.seed_count,
            keeps_seed_on_reset=True,
            role_id=session.role_id,
            role_display_name=role.display_name if role else None,
            role_version=role.version if role else None,
            role_source=_role_source_short(session),
            route_reason=session.route_reason or None,
        )
    few_shot = version_id == "v2_fewshot"
    return ViewerMeta(
        version_id=version_id,
        version_label=spec.label,
        few_shot=few_shot,
        seed_count=len(session.messages),
        keeps_seed_on_reset=True,
    )


def format_api_error(err: Exception, snap: MechanismSnapshot | None = None) -> str:
    msg = str(err).strip() or err.__class__.__name__
    lower = msg.lower()
    if "timed out" in lower or "timeout" in lower:
        base = snap.config.base_url if snap else DEFAULT_ZHIPU_BASE_URL
        return (
            f"请求超时：{msg}\n"
            "请检查：\n"
            f"  1. 接口应为 https://open.bigmodel.cn/api/paas/v4（当前 {base}）\n"
            "  2. 浏览器能否打开 open.bigmodel.cn\n"
            "  3. 仍慢可设 ZHIPU_TIMEOUT=180 后重启"
        )
    if "401" in msg or "authentication" in lower or ("invalid" in lower and "key" in lower):
        return f"鉴权失败：{msg}\n请确认 ZHIPU_API_KEY 正确且未过期。"
    return msg


SCOPE_CURRENT = "current"
SCOPE_ALL = "all"


def _scope_from_label(label: str) -> str:
    label = label.strip()
    if label == "全部历史":
        return SCOPE_ALL
    if label.startswith("第 ") and label.endswith("轮"):
        try:
            n = int(label[2:-1].strip())
            return f"round:{n}"
        except ValueError:
            pass
    return SCOPE_CURRENT


def _scope_to_label(scope: str) -> str:
    if scope == SCOPE_ALL:
        return "全部历史"
    if scope.startswith("round:"):
        return f"第 {scope.split(':', 1)[1]} 轮"
    return "当前（最新）"


def format_messages_for_scope(
    session: AgentSession | PromptAgentSession | None,
    snap: MechanismSnapshot | None,
    scope: str,
) -> str:
    if session is None:
        return "[]"
    history = session.turn_history
    if scope == SCOPE_ALL:
        if not history:
            return json.dumps(session.messages, ensure_ascii=False, indent=2)
        blocks: list[str] = []
        for rec in history:
            blocks.append(f"{'=' * 12} 第 {rec.round} 轮结束后 messages {'=' * 12}")
            blocks.append(json.dumps(rec.messages_after, ensure_ascii=False, indent=2))
        blocks.append(f"{'=' * 12} 当前最新 messages {'=' * 12}")
        blocks.append(json.dumps(session.messages, ensure_ascii=False, indent=2))
        return "\n\n".join(blocks)
    if scope.startswith("round:"):
        n = int(scope.split(":", 1)[1])
        for rec in history:
            if rec.round == n:
                header = f"第 {n} 轮结束后发给下一轮的 messages（共 {len(rec.messages_after)} 条）\n"
                header += "─" * 48 + "\n\n"
                return header + json.dumps(rec.messages_after, ensure_ascii=False, indent=2)
        return f"未找到第 {n} 轮记录。"
    # 当前（最新）
    msgs = snap.messages if snap else session.messages
    header = f"当前最新 messages（共 {len(msgs)} 条）\n" + "─" * 48 + "\n\n"
    return header + json.dumps(msgs, ensure_ascii=False, indent=2)


def _format_raw_dict(data: dict | None, empty_hint: str) -> str:
    if not data:
        return empty_hint
    return json.dumps(data, ensure_ascii=False, indent=2)


def _format_one_request(rec: TurnRecord) -> str:
    note = (rec.request or {}).get("note", "")
    step = f" · {note}" if note else ""
    head = f"第 {rec.round} 轮{step} · 发送 → LLM\n" + "─" * 40 + "\n\n"
    return head + _format_raw_dict(rec.request, "")


def _format_one_response(rec: TurnRecord) -> str:
    if rec.error:
        head = f"第 {rec.round} 轮 · 调用失败\n" + "─" * 40 + "\n\n"
        return head + rec.error
    head = f"第 {rec.round} 轮 · LLM → 返回\n" + "─" * 40 + "\n\n"
    return head + _format_raw_dict(rec.response, "（无响应体）")


def format_raw_for_scope(
    session: AgentSession | PromptAgentSession | None,
    snap: MechanismSnapshot | None,
    scope: str,
    err: str | None = None,
) -> tuple[str, str]:
    empty_req = (
        "尚无请求。\n\n发送消息后，可在此查看各轮发给 LLM 的原始请求；"
        "上方「查看范围」可切换当前 / 某一轮 / 全部历史。"
    )
    empty_resp = (
        "尚无响应。\n\n成功调用后显示 LLM 返回的原始 JSON（choices、usage 等）。"
    )
    if session is None:
        return empty_req, err or empty_resp

    history = session.turn_history

    if scope == SCOPE_ALL:
        if not history:
            req = _format_raw_dict(snap.last_request if snap else None, empty_req)
            resp = format_raw_response_latest(snap, err, empty_resp)
            return req, resp
        req_parts = [_format_one_request(r) for r in history]
        resp_parts = [_format_one_response(r) for r in history]
        return "\n\n".join(req_parts), "\n\n".join(resp_parts)

    if scope.startswith("round:"):
        n = int(scope.split(":", 1)[1])
        for rec in history:
            if rec.round == n:
                return _format_one_request(rec), _format_one_response(rec)
        return f"未找到第 {n} 轮请求。", f"未找到第 {n} 轮响应。"

    return format_raw_request_latest(snap, err, empty_req, empty_resp)


def format_raw_request_latest(
    snap: MechanismSnapshot | None,
    err: str | None,
    empty_req: str,
    empty_resp: str,
) -> tuple[str, str]:
    del empty_resp
    if snap and snap.last_request:
        head = f"第 {snap.round} 轮 · 发送 → LLM（当前最新）\n" + "─" * 40 + "\n\n"
        req = head + _format_raw_dict(snap.last_request, "")
    else:
        req = empty_req
    resp = format_raw_response_latest(snap, err, "尚无响应。")
    return req, resp


def format_raw_response_latest(
    snap: MechanismSnapshot | None, err: str | None, empty_resp: str
) -> str:
    if err and snap and not snap.last_response:
        head = f"第 {snap.round} 轮 · 调用失败\n" + "─" * 40 + "\n\n"
        return head + err
    if not snap or not snap.last_response:
        return empty_resp
    head = f"第 {snap.round} 轮 · LLM → 返回（当前最新）\n" + "─" * 40 + "\n\n"
    return head + _format_raw_dict(snap.last_response, "")


def startup_message(meta: ViewerMeta) -> str:
    if meta.version_id == "v1_minimal":
        return f"已加载 {meta.version_label}。首轮 messages 为空，见右侧「messages JSON」。"
    fs = "Few-shot 已注入" if meta.few_shot else "Zero-shot（无范例）"
    msg = f"已加载 {meta.version_label}；{fs}。"
    if _is_v3(meta.version_id) or _is_v4(meta.version_id):
        if meta.role_id:
            name = meta.role_display_name or meta.role_id
            ver = f" v{meta.role_version}" if meta.role_version else ""
            msg += f" 角色: {name} ({meta.role_id}{ver}) · 选角: {meta.role_source or '—'}"
            if meta.route_reason:
                msg += f" · 依据: {meta.route_reason}"
            msg += "。"
        else:
            msg += f" 选角: {meta.role_source or '待路由'}。"
        if _is_v4(meta.version_id):
            mode = "简化 ToT + CoT" if meta.tot_enabled else "CoT"
            msg += f" 推理: {mode}。"
    elif _is_v6(meta.version_id) or _is_v7(meta.version_id):
        msg += " 一体化运行机制（自动选角、按需比选/精炼）。"
        if _is_v7(meta.version_id):
            msg += " 工具含 read/write/done；详情见「运行轨迹」与机制面板 ReAct 区。"
        else:
            msg += " ReAct + calculator；详情见「运行轨迹」。"
    if meta.seed_count:
        msg += f" 种子 {meta.seed_count} 条，见右侧 JSON。"
    elif _is_v3(meta.version_id) or _is_v4(meta.version_id):
        msg += " 发送首条消息后注入固定前缀。"
    elif _is_v6(meta.version_id) or _is_v7(meta.version_id):
        msg += " 发送首条消息后加载角色与 Few-shot。"
    else:
        msg += " 见右侧 JSON。"
    return msg


class HistoryScopeBar(tk.Frame):
    """messages JSON / API 原始报文共用的「查看范围」选择器。"""

    def __init__(self, parent: tk.Misc, on_change: Any) -> None:
        super().__init__(parent, bg=C_SURFACE, padx=8, pady=6)
        self._on_change = on_change
        self._scope = SCOPE_CURRENT

        tk.Label(
            self,
            text="查看范围",
            font=("Microsoft YaHei UI", 9),
            fg=C_MUTED,
            bg=C_SURFACE,
        ).pack(side=tk.LEFT, padx=(0, 8))

        self._label_var = tk.StringVar(value=_scope_to_label(SCOPE_CURRENT))
        self.combo = ttk.Combobox(
            self,
            textvariable=self._label_var,
            values=["当前（最新）", "全部历史"],
            state="readonly",
            width=18,
            font=("Microsoft YaHei UI", 9),
        )
        self.combo.pack(side=tk.LEFT)
        self.combo.bind("<<ComboboxSelected>>", self._on_select)

        tk.Label(
            self,
            text="切换版本无需退出程序；聊天区保留历史并插入分隔线",
            font=("Microsoft YaHei UI", 8),
            fg=C_MUTED,
            bg=C_SURFACE,
        ).pack(side=tk.LEFT, padx=(12, 0))

    def _on_select(self, _event: Any = None) -> None:
        self._scope = _scope_from_label(self._label_var.get())
        self._on_change()

    def get_scope(self) -> str:
        return self._scope

    def set_scope(self, scope: str) -> None:
        self._scope = scope
        self._label_var.set(_scope_to_label(scope))

    def sync_rounds(self, round_count: int) -> None:
        opts = ["当前（最新）", "全部历史"]
        opts.extend(f"第 {i} 轮" for i in range(1, round_count + 1))
        self.combo.configure(values=opts)
        if self._scope.startswith("round:"):
            n = int(self._scope.split(":", 1)[1])
            if n > round_count:
                self.set_scope(SCOPE_CURRENT)


def _bind_mousewheel(canvas: tk.Canvas, widget: tk.Widget) -> None:
    def _on_wheel(event: tk.Event) -> None:
        if event.delta:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        elif event.num == 4:
            canvas.yview_scroll(-3, "units")
        elif event.num == 5:
            canvas.yview_scroll(3, "units")

    widget.bind("<Enter>", lambda _e: widget.bind_all("<MouseWheel>", _on_wheel))
    widget.bind("<Leave>", lambda _e: widget.unbind_all("<MouseWheel>"))
    widget.bind("<Enter>", lambda _e: widget.bind_all("<Button-4>", _on_wheel))
    widget.bind("<Enter>", lambda _e: widget.bind_all("<Button-5>", _on_wheel))


class RawApiPanel(tk.Frame):
    """最近一轮 API 原始请求 / 响应（上下分栏）。"""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, bg=C_BG)
        paned = tk.PanedWindow(self, orient=tk.VERTICAL, bg=C_BG, sashwidth=6)
        paned.pack(fill=tk.BOTH, expand=True)

        req_wrap = self._section("发送 → LLM（原始请求）", "#1e3a5f")
        paned.add(req_wrap, minsize=120)
        self.request_text = self._code_text(req_wrap.body)
        self.request_text.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

        resp_wrap = self._section("LLM → 返回（原始响应）", "#14532d")
        paned.add(resp_wrap, minsize=120)
        self.response_text = self._code_text(resp_wrap.body)
        self.response_text.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

    def _section(self, title: str, bar_color: str) -> tk.Frame:
        """返回整块卡片（标题条 + 内容区）；须作为 PanedWindow 的直接子组件 add。"""
        wrap = tk.Frame(
            self,
            bg=C_SURFACE,
            highlightbackground=C_BORDER,
            highlightthickness=1,
        )
        bar = tk.Frame(wrap, bg=bar_color, height=28)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)
        tk.Label(
            bar,
            text=title,
            font=("Microsoft YaHei UI", 9, "bold"),
            fg="#ffffff",
            bg=bar_color,
        ).pack(side=tk.LEFT, padx=10, pady=4)
        wrap.body = tk.Frame(wrap, bg=C_SURFACE)  # type: ignore[attr-defined]
        wrap.body.pack(fill=tk.BOTH, expand=True)
        return wrap

    @staticmethod
    def _code_text(parent: tk.Frame) -> scrolledtext.ScrolledText:
        return scrolledtext.ScrolledText(
            parent,
            wrap=tk.WORD,
            font=("Consolas", 9),
            state=tk.DISABLED,
            bg="#0f172a",
            fg="#e2e8f0",
            insertbackground="#e2e8f0",
            relief=tk.FLAT,
            padx=6,
            pady=6,
        )

    @staticmethod
    def _fill(widget: scrolledtext.ScrolledText, content: str) -> None:
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, content)
        widget.configure(state=tk.DISABLED)

    def update_scope(
        self,
        session: AgentSession | PromptAgentSession | None,
        snap: MechanismSnapshot | None,
        scope: str,
        err: str | None = None,
    ) -> None:
        req, resp = format_raw_for_scope(session, snap, scope, err)
        self._fill(self.request_text, req)
        self._fill(self.response_text, resp)

    def show_empty(self, err: str | None = None) -> None:
        self._fill(
            self.request_text,
            "尚无请求。发送一条消息后显示最近一轮发给 LLM 的原始报文。",
        )
        self._fill(
            self.response_text,
            err or "尚无响应。成功调用后显示 LLM 返回的原始 JSON。",
        )


def _split_message_stats(
    snap: MechanismSnapshot, meta: ViewerMeta
) -> tuple[int, int, int]:
    """返回 (种子字符数, 当轮聊天字符数, 种子内范例对数)。"""
    seed_n = meta.seed_count
    msgs = snap.messages
    if seed_n <= 0 or len(msgs) < seed_n:
        return 0, snap.approx_chars_in_messages, 0
    seed_chars = sum(len(str(m.get("content", ""))) for m in msgs[:seed_n])
    runtime_chars = max(0, snap.approx_chars_in_messages - seed_chars)
    # v2：首条多为 system，其余为 Few-shot 的 user/assistant 对
    seed_pairs = max(0, (seed_n - 1) // 2) if meta.few_shot else 0
    return seed_chars, runtime_chars, seed_pairs


class RoleSettingPanel(tk.Frame):
    """第04篇 v3 专用：当前角色、选角依据、compose_system 预览。"""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, bg=C_BG)
        self._value_labels: dict[str, tk.Label] = {}

        info = tk.Frame(
            self,
            bg=C_SURFACE,
            highlightbackground=C_BORDER,
            highlightthickness=1,
            padx=12,
            pady=10,
        )
        info.pack(fill=tk.X, padx=4, pady=(4, 6))

        for label, key in (
            ("角色 id", "rs_id"),
            ("展示名", "rs_name"),
            ("版本", "rs_ver"),
            ("角色文件", "rs_path"),
            ("选角来源", "rs_src"),
            ("选角依据", "rs_reason"),
            ("Few-shot 种子", "rs_few"),
        ):
            row = tk.Frame(info, bg=C_SURFACE)
            row.pack(fill=tk.X, pady=2)
            tk.Label(
                row,
                text=label,
                font=("Microsoft YaHei UI", 9),
                fg=C_MUTED,
                bg=C_SURFACE,
                width=12,
                anchor=tk.W,
            ).pack(side=tk.LEFT)
            val = tk.Label(
                row,
                text="—",
                font=("Microsoft YaHei UI", 9),
                fg=C_TEXT,
                bg=C_SURFACE,
                anchor=tk.W,
                justify=tk.LEFT,
                wraplength=420,
            )
            val.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self._value_labels[key] = val

        tk.Label(
            self,
            text="角色 Prompt（第一条 role: system 的 content，与发往 API 一致）",
            font=("Microsoft YaHei UI", 9, "bold"),
            fg=C_TEXT,
            bg=C_BG,
            anchor=tk.W,
        ).pack(fill=tk.X, padx=8, pady=(4, 2))

        prompt_wrap = tk.Frame(
            self,
            bg=C_SURFACE,
            highlightbackground=C_BORDER,
            highlightthickness=1,
        )
        prompt_wrap.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))
        self._prompt_text = scrolledtext.ScrolledText(
            prompt_wrap,
            wrap=tk.WORD,
            font=("Microsoft YaHei UI", 9),
            fg=C_TEXT,
            bg="#f8fafc",
            relief=tk.FLAT,
            padx=8,
            pady=8,
        )
        self._prompt_text.pack(fill=tk.BOTH, expand=True)
        self._prompt_text.configure(state=tk.DISABLED)

        tk.Label(
            self,
            text="提示：非第04篇版本时本页仅作说明；范例对全文见「messages JSON」。",
            font=("Microsoft YaHei UI", 8),
            fg=C_MUTED,
            bg=C_BG,
            justify=tk.LEFT,
            wraplength=480,
        ).pack(fill=tk.X, padx=8, pady=(0, 6))

    def _set(self, key: str, text: str) -> None:
        lbl = self._value_labels.get(key)
        if lbl:
            lbl.configure(text=text)

    def _set_prompt(self, text: str) -> None:
        self._prompt_text.configure(state=tk.NORMAL)
        self._prompt_text.delete("1.0", tk.END)
        self._prompt_text.insert(tk.END, text or "（暂无）")
        self._prompt_text.configure(state=tk.DISABLED)

    def update_panel(
        self,
        meta: ViewerMeta,
        session: AgentSession | PromptAgentSession | RoleAgentSession | None,
    ) -> None:
        if not _is_role_agent(meta.version_id):
            for key in self._value_labels:
                self._set(key, "—")
            self._set_prompt("当前 Agent 版本无角色设定（请切换到 v3/v4 条目）。")
            return

        if not isinstance(session, (RoleAgentSession, CotAgentSession)):
            for key in self._value_labels:
                self._set(key, "—")
            self._set_prompt("（会话未就绪）")
            return

        if session.role is None or session.role_id is None:
            self._set("rs_id", "—")
            self._set("rs_name", "—")
            self._set("rs_ver", "—")
            self._set("rs_path", "—")
            self._set("rs_src", meta.role_source or "待路由")
            self._set("rs_reason", "—（发送首条 user 后由 role_router 生成）")
            self._set("rs_few", "—")
            self._set_prompt(
                "AGENT_ROLE=auto：固定前缀尚未注入。\n"
                "请发送首条 user 消息；选角完成后本页将显示 compose_system 结果。"
            )
            return

        role = session.role
        self._set("rs_id", role.id)
        self._set("rs_name", role.display_name)
        self._set("rs_ver", role.version)
        self._set("rs_path", f"role_setting_v3/prompts/roles/{role.id}.yaml")
        self._set("rs_src", meta.role_source or _role_source_short(session))
        reason = meta.route_reason or session.route_reason or ""
        if meta.role_source == "指定" or session.role_source == "manual":
            self._set("rs_reason", "—（指定选角，无路由依据）")
        else:
            self._set("rs_reason", reason or "—")
        few_hint = _few_shot_seed_hint(session, meta)
        if _is_v4(meta.version_id) and meta.include_cot:
            few_hint += "；含 CoT 格式约束"
        self._set("rs_few", few_hint)

        preview = _role_prompt_preview(session)
        if preview:
            self._set_prompt(preview)
        else:
            self._set_prompt("（无法生成预览）")


class ReasoningPanel(tk.Frame):
    """v4 agent：CoT 分段与简化 ToT 观测。"""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, bg=C_BG)
        self._value_labels: dict[str, tk.Label] = {}
        info = tk.Frame(
            self, bg=C_SURFACE, highlightbackground=C_BORDER, highlightthickness=1,
            padx=12, pady=10,
        )
        info.pack(fill=tk.X, padx=4, pady=(4, 6))
        for label, key in (
            ("CoT 格式", "rn_cot"),
            ("ToT 候选数", "rn_n"),
            ("选中计划", "rn_sel"),
            ("比选依据", "rn_reason"),
        ):
            row = tk.Frame(info, bg=C_SURFACE)
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=label, font=("Microsoft YaHei UI", 9), fg=C_MUTED,
                     bg=C_SURFACE, width=12, anchor=tk.W).pack(side=tk.LEFT)
            val = tk.Label(row, text="—", font=("Microsoft YaHei UI", 9), fg=C_TEXT,
                           bg=C_SURFACE, anchor=tk.W, wraplength=420, justify=tk.LEFT)
            val.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self._value_labels[key] = val
        for title, attr in (("## 推理", "_r"), ("## 结论", "_c"), ("ToT 计划", "_p")):
            tk.Label(self, text=title, font=("Microsoft YaHei UI", 9, "bold"),
                     fg=C_TEXT, bg=C_BG, anchor=tk.W).pack(fill=tk.X, padx=8, pady=(4, 2))
            wrap = tk.Frame(self, bg=C_SURFACE, highlightbackground=C_BORDER, highlightthickness=1)
            wrap.pack(fill=tk.BOTH, expand=(attr == "_r"), padx=4, pady=(0, 4))
            box = scrolledtext.ScrolledText(wrap, wrap=tk.WORD, height=5 if attr != "_r" else 7,
                font=("Microsoft YaHei UI", 9), fg=C_TEXT, bg="#f8fafc", relief=tk.FLAT, padx=8, pady=8)
            box.pack(fill=tk.BOTH, expand=True)
            box.configure(state=tk.DISABLED)
            setattr(self, attr, box)

    def _set(self, key: str, text: str, *, fg: str | None = None) -> None:
        lbl = self._value_labels.get(key)
        if lbl:
            lbl.configure(text=text)
            if fg:
                lbl.configure(fg=fg)

    def _fill(self, w: scrolledtext.ScrolledText, text: str) -> None:
        w.configure(state=tk.NORMAL)
        w.delete("1.0", tk.END)
        w.insert(tk.END, text or "（暂无）")
        w.configure(state=tk.DISABLED)

    def update_panel(
        self, meta: ViewerMeta,
        session: AgentSession | PromptAgentSession | RoleAgentSession | CotAgentSession | None,
    ) -> None:
        if not _is_reasoning(meta.version_id) or not isinstance(session, CotAgentSession):
            for k in self._value_labels:
                self._set(k, "—")
            self._fill(self._r, "请切换到 v4/v5 推理 Agent 版本。")
            self._fill(self._c, "")
            self._fill(self._p, "")
            return
        if session.last_cot and session.cot_format_ok():
            self._set("rn_cot", "合规", fg=C_SUCCESS)
        elif session.last_cot:
            self._set("rn_cot", "未合规", fg=C_ERROR)
        else:
            self._set("rn_cot", "—")
        if session.last_plans:
            self._set("rn_n", str(len(session.last_plans)))
            self._set("rn_sel", (session.selected_plan or "—")[:120])
            self._set("rn_reason", session.plan_select_reason or "—")
            lines = [f"{i}. {p}{' ← 选中' if p == session.selected_plan else ''}"
                     for i, p in enumerate(session.last_plans, 1)]
            self._fill(self._p, "\n\n".join(lines))
        elif getattr(session, "last_consistency", None):
            lc = session.last_consistency
            self._set("rn_n", str(len(lc.conclusions)))
            self._set("rn_sel", (session.consensus_conclusion or "—")[:120])
            self._set(
                "rn_reason",
                f"一致率 {session.agreement_rate:.0%}（{lc.winner_count}/{len(lc.conclusions)}）",
            )
            lines = [
                f"样本{i}: {c}{' ← 众数' if c.strip() == session.consensus_conclusion.strip() else ''}"
                for i, c in enumerate(lc.conclusions, 1)
            ]
            self._fill(self._p, "\n\n".join(lines))
        elif getattr(session, "last_graph_branches", None) and session.last_graph_branches:
            branches = session.last_graph_branches
            self._set("rn_n", str(len(branches)))
            self._set("rn_sel", "并行汇总 → 主对话")
            self._set("rn_reason", "fan-out / fan-in")
            lines = [f"{i}. {b.question}\n   → {b.answer[:200]}" for i, b in enumerate(branches, 1)]
            self._fill(self._p, "\n\n".join(lines))
        else:
            self._set("rn_n", "—")
            self._set("rn_sel", "—")
            self._set("rn_reason", "—")
            self._fill(self._p, "—")
        if session.last_cot:
            self._fill(self._r, session.last_cot.reasoning)
            self._fill(self._c, session.last_cot.conclusion)
        else:
            self._fill(self._r, "—")
            self._fill(self._c, "—")


class QualityPanel(tk.Frame):
    """reflection_v5：自洽性、批评与精炼旁路观测。"""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, bg=C_BG)
        self._value_labels: dict[str, tk.Label] = {}
        info = tk.Frame(
            self, bg=C_SURFACE, highlightbackground=C_BORDER, highlightthickness=1,
            padx=12, pady=10,
        )
        info.pack(fill=tk.X, padx=4, pady=(4, 6))
        for label, key in (
            ("质检模式", "qn_mode"),
            ("一致率 / 状态", "qn_rate"),
            ("众数结论", "qn_winner"),
        ):
            row = tk.Frame(info, bg=C_SURFACE)
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=label, font=("Microsoft YaHei UI", 9), fg=C_MUTED,
                     bg=C_SURFACE, width=14, anchor=tk.W).pack(side=tk.LEFT)
            val = tk.Label(row, text="—", font=("Microsoft YaHei UI", 9), fg=C_TEXT,
                           bg=C_SURFACE, anchor=tk.W, wraplength=420, justify=tk.LEFT)
            val.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self._value_labels[key] = val
        for title, attr, height in (
            ("自洽性 · 各次结论", "_samples", 5),
            ("初稿（批评前）", "_draft", 6),
            ("批评意见", "_critique", 5),
            ("修订稿", "_refined", 6),
        ):
            tk.Label(self, text=title, font=("Microsoft YaHei UI", 9, "bold"),
                     fg=C_TEXT, bg=C_BG, anchor=tk.W).pack(fill=tk.X, padx=8, pady=(4, 2))
            wrap = tk.Frame(self, bg=C_SURFACE, highlightbackground=C_BORDER, highlightthickness=1)
            wrap.pack(fill=tk.BOTH, expand=(attr == "_draft"), padx=4, pady=(0, 4))
            box = scrolledtext.ScrolledText(
                wrap, wrap=tk.WORD, height=height,
                font=("Microsoft YaHei UI", 9), fg=C_TEXT, bg="#f8fafc",
                relief=tk.FLAT, padx=8, pady=8,
            )
            box.pack(fill=tk.BOTH, expand=True)
            box.configure(state=tk.DISABLED)
            setattr(self, attr, box)

    def _set(self, key: str, text: str, *, fg: str | None = None) -> None:
        lbl = self._value_labels.get(key)
        if lbl:
            lbl.configure(text=text)
            if fg:
                lbl.configure(fg=fg)

    def _fill(self, w: scrolledtext.ScrolledText, text: str) -> None:
        w.configure(state=tk.NORMAL)
        w.delete("1.0", tk.END)
        w.insert(tk.END, text or "（暂无）")
        w.configure(state=tk.DISABLED)

    def update_panel(
        self, meta: ViewerMeta,
        session: AgentSession | PromptAgentSession | RoleAgentSession | CotAgentSession | None,
    ) -> None:
        if not isinstance(session, ReflectionAgentSession):
            self._set("qn_mode", "—")
            self._set("qn_rate", "—")
            self._set("qn_winner", "—")
            for attr in ("_samples", "_draft", "_critique", "_refined"):
                self._fill(getattr(self, attr), "请切换到第06篇 reflection_v5 版本。")
            return

        mode = session.quality_mode
        mode_label = {
            "off": "关闭",
            "consistency": "自洽性",
            "refine": "批评 + 精炼",
            "all": "全开",
        }.get(mode, mode)
        self._set("qn_mode", mode_label)

        if session.last_consistency:
            lc = session.last_consistency
            rate_text = (
                f"{session.agreement_rate:.0%} "
                f"（{lc.winner_count}/{len(lc.conclusions)}）"
            )
            if session.consistency_below_threshold:
                self._set("qn_rate", rate_text + " · 低于阈值", fg=C_ERROR)
            else:
                self._set("qn_rate", rate_text, fg=C_SUCCESS)
            self._set("qn_winner", (session.consensus_conclusion or "—")[:120])
            lines = [
                f"样本{i}: {c}{' ← 众数' if c.strip() == session.consensus_conclusion.strip() else ''}"
                for i, c in enumerate(lc.conclusions, 1)
            ]
            self._fill(self._samples, "\n\n".join(lines))
        else:
            self._set("qn_rate", "—" if mode != "consistency" else "尚无采样")
            self._set("qn_winner", "—")
            self._fill(self._samples, "—")

        self._fill(self._draft, session.last_draft or "—")
        self._fill(self._critique, session.last_critique or "—")
        self._fill(self._refined, session.last_refined or "—")


class ToolsPanel(tk.Frame):
    """react_v6：ReAct 工具调用链观测（可选 Tab）。"""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, bg=C_BG)
        self._value_labels: dict[str, tk.Label] = {}
        info = tk.Frame(
            self, bg=C_SURFACE, highlightbackground=C_BORDER, highlightthickness=1,
            padx=12, pady=10,
        )
        info.pack(fill=tk.X, padx=4, pady=(4, 6))
        for label, key in (
            ("ReAct 模式", "tl_mode"),
            ("API 轮次", "tl_rounds"),
            ("工具步数", "tl_steps"),
        ):
            row = tk.Frame(info, bg=C_SURFACE)
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=label, font=("Microsoft YaHei UI", 9), fg=C_MUTED,
                     bg=C_SURFACE, width=14, anchor=tk.W).pack(side=tk.LEFT)
            val = tk.Label(row, text="—", font=("Microsoft YaHei UI", 9), fg=C_TEXT,
                           bg=C_SURFACE, anchor=tk.W, wraplength=420, justify=tk.LEFT)
            val.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self._value_labels[key] = val
        tk.Label(self, text="工具调用链（tool_call → Observation）",
                 font=("Microsoft YaHei UI", 9, "bold"), fg=C_TEXT, bg=C_BG,
                 anchor=tk.W).pack(fill=tk.X, padx=8, pady=(4, 2))
        wrap = tk.Frame(self, bg=C_SURFACE, highlightbackground=C_BORDER, highlightthickness=1)
        wrap.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))
        self._steps = scrolledtext.ScrolledText(
            wrap, wrap=tk.WORD, height=14,
            font=("Consolas", 9), fg=C_TEXT, bg="#f8fafc",
            relief=tk.FLAT, padx=8, pady=8,
        )
        self._steps.pack(fill=tk.BOTH, expand=True)
        self._steps.configure(state=tk.DISABLED)

    def _set(self, key: str, text: str, *, fg: str | None = None) -> None:
        lbl = self._value_labels.get(key)
        if lbl:
            lbl.configure(text=text)
            if fg:
                lbl.configure(fg=fg)

    def _fill(self, w: scrolledtext.ScrolledText, text: str) -> None:
        w.configure(state=tk.NORMAL)
        w.delete("1.0", tk.END)
        w.insert(tk.END, text or "（暂无）")
        w.configure(state=tk.DISABLED)

    def update_panel(
        self, meta: ViewerMeta,
        session: AgentSession | PromptAgentSession | RoleAgentSession | CotAgentSession | None,
    ) -> None:
        if not _is_commercial_react_session(session):
            self._set("tl_mode", "—")
            self._set("tl_rounds", "—")
            self._set("tl_steps", "—")
            self._fill(self._steps, "请切换到第07篇 v6 或第08篇 v7 版本。")
            return
        self._set("tl_mode", "一体化（始终开启）")
        self._set("tl_rounds", str(session.react_steps_used or "—"))
        n_tools = len(session.last_tool_steps)
        step_text = str(n_tools)
        if session.react_hit_limit:
            self._set("tl_steps", step_text + " · 已达上限", fg=C_WARN)
        else:
            self._set("tl_steps", step_text, fg=C_SUCCESS if n_tools else C_TEXT)
        lines: list[str] = []
        for step in session.last_tool_steps:
            status = "OK" if step.ok else "FAIL"
            lines.append(
                f"步骤 {step.step} [{status}] {step.tool_name}\n"
                f"  参数: {step.arguments}\n"
                f"  Observation: {step.observation}\n"
            )
        self._fill(self._steps, "\n".join(lines) if lines else "本轮尚无工具调用。")


class TrajectoryPanel(tk.Frame):
    """react_v6：本轮实际启用的机制与工具链（运行轨迹）。"""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, bg=C_BG)
        tk.Label(
            self, text="本轮运行轨迹（程序自动决策，无需手选机制）",
            font=("Microsoft YaHei UI", 9, "bold"), fg=C_TEXT, bg=C_BG, anchor=tk.W,
        ).pack(fill=tk.X, padx=8, pady=(4, 2))
        wrap1 = tk.Frame(self, bg=C_SURFACE, highlightbackground=C_BORDER, highlightthickness=1)
        wrap1.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))
        self._trace = scrolledtext.ScrolledText(
            wrap1, wrap=tk.WORD, height=10,
            font=("Microsoft YaHei UI", 9), fg=C_TEXT, bg="#f8fafc",
            relief=tk.FLAT, padx=8, pady=8,
        )
        self._trace.pack(fill=tk.BOTH, expand=True)
        self._trace.configure(state=tk.DISABLED)
        tk.Label(
            self, text="工具调用链",
            font=("Microsoft YaHei UI", 9, "bold"), fg=C_TEXT, bg=C_BG, anchor=tk.W,
        ).pack(fill=tk.X, padx=8, pady=(4, 2))
        wrap2 = tk.Frame(self, bg=C_SURFACE, highlightbackground=C_BORDER, highlightthickness=1)
        wrap2.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))
        self._tools = scrolledtext.ScrolledText(
            wrap2, wrap=tk.WORD, height=8,
            font=("Consolas", 9), fg=C_TEXT, bg="#f8fafc",
            relief=tk.FLAT, padx=8, pady=8,
        )
        self._tools.pack(fill=tk.BOTH, expand=True)
        self._tools.configure(state=tk.DISABLED)

    def _fill(self, w: scrolledtext.ScrolledText, text: str) -> None:
        w.configure(state=tk.NORMAL)
        w.delete("1.0", tk.END)
        w.insert(tk.END, text or "（暂无）")
        w.configure(state=tk.DISABLED)

    def update_panel(
        self, meta: ViewerMeta,
        session: AgentSession | PromptAgentSession | RoleAgentSession | CotAgentSession | None,
    ) -> None:
        if not _is_commercial_react_session(session):
            self._fill(self._trace, "请使用第07篇 v6 或第08篇 v7 版本。")
            self._fill(self._tools, "—")
            return
        trace = session.runtime_trace
        if trace:
            self._fill(self._trace, trace.as_text())
        else:
            self._fill(self._trace, "发送消息后显示本轮自动启用的机制。")
        lines: list[str] = []
        for step in session.last_tool_steps:
            status = "OK" if step.ok else "FAIL"
            lines.append(
                f"步骤 {step.step} [{status}] {step.tool_name}\n"
                f"  参数: {step.arguments}\n"
                f"  Observation: {step.observation}\n"
            )
        self._fill(self._tools, "\n".join(lines) if lines else "本轮无工具调用。")


class MechanismDashboard(tk.Frame):
    """右侧机制面板：卡片 + 指标块，替代纯文本。"""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, bg=C_BG)
        self._value_labels: dict[str, tk.Label] = {}
        self._badge_label: tk.Label | None = None
        self._error_label: tk.Label | None = None

        self._canvas = tk.Canvas(self, bg=C_BG, highlightthickness=0, borderwidth=0)
        self._scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self._canvas.yview)
        self._inner = tk.Frame(self._canvas, bg=C_BG)
        self._win_id = self._canvas.create_window((0, 0), window=self._inner, anchor=tk.NW)

        self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._canvas.configure(yscrollcommand=self._scrollbar.set)

        self._inner.bind("<Configure>", self._on_inner_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        _bind_mousewheel(self._canvas, self._canvas)

        self._build_layout()

    def _on_inner_configure(self, _event: tk.Event | None = None) -> None:
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self._canvas.itemconfigure(self._win_id, width=event.width)

    def _card(self, parent: tk.Frame, title: str) -> tk.Frame:
        outer = tk.Frame(parent, bg=C_BG)
        outer.pack(fill=tk.X, pady=(0, 10))
        box = tk.Frame(
            outer,
            bg=C_SURFACE,
            highlightbackground=C_BORDER,
            highlightthickness=1,
            padx=14,
            pady=12,
        )
        box.pack(fill=tk.X)
        tk.Label(
            box,
            text=title,
            font=("Microsoft YaHei UI", 10, "bold"),
            fg=C_TEXT,
            bg=C_SURFACE,
            anchor=tk.W,
        ).pack(fill=tk.X, pady=(0, 8))
        body = tk.Frame(box, bg=C_SURFACE)
        body.pack(fill=tk.X)
        return body

    def _stat_tile(
        self, parent: tk.Frame, title: str, key: str, accent: str
    ) -> None:
        tile = tk.Frame(
            parent,
            bg=C_SURFACE,
            highlightbackground=C_BORDER,
            highlightthickness=1,
            padx=10,
            pady=10,
        )
        tile.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        tk.Label(
            tile, text=title, font=("Microsoft YaHei UI", 8), fg=C_MUTED, bg=C_SURFACE
        ).pack(anchor=tk.W)
        val = tk.Label(
            tile,
            text="—",
            font=("Segoe UI", 14, "bold"),
            fg=accent,
            bg=C_SURFACE,
            anchor=tk.W,
        )
        val.pack(anchor=tk.W, pady=(2, 0))
        self._value_labels[key] = val
        parent._last_tile = tile  # type: ignore[attr-defined]

    def _row(self, parent: tk.Frame, label: str, key: str, *, mono: bool = False) -> None:
        row = tk.Frame(parent, bg=C_SURFACE)
        row.pack(fill=tk.X, pady=3)
        tk.Label(
            row,
            text=label,
            font=("Microsoft YaHei UI", 9),
            fg=C_MUTED,
            bg=C_SURFACE,
            width=14,
            anchor=tk.W,
        ).pack(side=tk.LEFT)
        font: tuple[str, int] | tuple[str, int, str] = (
            ("Consolas", 9) if mono else ("Microsoft YaHei UI", 9)
        )
        val = tk.Label(row, text="—", font=font, fg=C_TEXT, bg=C_SURFACE, anchor=tk.W)
        val.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._value_labels[key] = val

    def _build_layout(self) -> None:
        p = self._inner

        hero = tk.Frame(p, bg=C_BG)
        hero.pack(fill=tk.X, pady=(4, 4))
        self._stat_tile(hero, "messages 条数", "stat_messages", C_STAT_MESSAGES)
        self._stat_tile(hero, "已完成轮次", "stat_rounds", C_STAT_ROUNDS)
        last = hero._last_tile  # type: ignore[attr-defined]
        last.pack_configure(padx=(0, 0))
        self._stat_tile(hero, "累计 Token", "stat_tokens", C_STAT_TOKENS)

        ver_body = self._card(p, "Agent 版本")
        top_row = tk.Frame(ver_body, bg=C_SURFACE)
        top_row.pack(fill=tk.X, pady=(0, 6))
        self._badge_label = tk.Label(
            top_row,
            text="—",
            font=("Microsoft YaHei UI", 8, "bold"),
            padx=8,
            pady=2,
        )
        self._badge_label.pack(side=tk.LEFT)
        self._row(ver_body, "当前版本", "ver_label")
        self._row(ver_body, "结构说明", "ver_structure")
        self._row(ver_body, "种子条数", "ver_seed")
        self._row(ver_body, "当前角色", "ver_role")
        self._row(ver_body, "选角来源", "ver_role_src")
        self._row(ver_body, "选角依据", "ver_route_reason")

        react_body = self._card(p, "ReAct · 本轮")
        self._row(react_body, "注册工具", "react_tools")
        self._row(react_body, "工作区", "react_workspace")
        self._row(react_body, "LLM · 工具", "react_steps")
        self._row(react_body, "done 验收", "react_done")

        cfg_body = self._card(p, "运行配置")
        self._row(cfg_body, "模型", "cfg_model")
        self._row(cfg_body, "接口", "cfg_url", mono=True)
        self._row(cfg_body, "temperature", "cfg_temp")
        self._row(cfg_body, "max_tokens", "cfg_maxtok")
        self._row(cfg_body, "API Key", "cfg_key")

        state_body = self._card(p, "对话状态")
        self._row(state_body, "messages 构成", "st_msg_breakdown")
        self._row(state_body, "已聊天轮数", "st_rounds")
        self._row(state_body, "种子占用字符", "st_seed_chars")
        self._row(state_body, "当轮聊天字符", "st_runtime_chars")

        tok_body = self._card(p, "Token · 计费")
        self._row(tok_body, "本轮", "tok_round")
        self._row(tok_body, "累计", "tok_total")

        self._error_label = tk.Label(
            p,
            text="",
            font=("Microsoft YaHei UI", 9),
            fg=C_ERROR,
            bg=C_ERROR_BG,
            padx=10,
            pady=8,
            justify=tk.LEFT,
            wraplength=320,
        )

        tk.Label(
            p,
            text="提示：未发消息前，Few-shot 版本的数字来自 system/范例种子，不是上次会话残留。",
            font=("Microsoft YaHei UI", 8),
            fg=C_MUTED,
            bg=C_BG,
            justify=tk.LEFT,
            wraplength=340,
        ).pack(fill=tk.X, pady=(4, 8))

    def _set(self, key: str, text: str, *, fg: str | None = None) -> None:
        lbl = self._value_labels.get(key)
        if lbl:
            lbl.configure(text=text)
            if fg:
                lbl.configure(fg=fg)

    def _set_badge(self, text: str, bg: str, fg: str) -> None:
        if self._badge_label:
            self._badge_label.configure(text=text, bg=bg, fg=fg)

    def update_dashboard(
        self,
        snap: MechanismSnapshot,
        meta: ViewerMeta,
        session: AgentSession | PromptAgentSession | RoleAgentSession | CotAgentSession | None = None,
    ) -> None:
        if self._error_label:
            self._error_label.pack_forget()

        cfg = snap.config
        temp = "模型默认" if cfg.temperature is None else str(cfg.temperature)
        max_tok = "模型默认" if cfg.max_tokens is None else str(cfg.max_tokens)
        key_hint = "已设置 ✓" if cfg.api_key_set else "未检测到"
        key_color = C_SUCCESS if cfg.api_key_set else C_ERROR

        if snap.last_usage is None:
            tok_round = "—（尚未发起或厂商未返回）"
        else:
            u = snap.last_usage
            tok_round = f"输入 {u.prompt_tokens} + 输出 {u.completion_tokens} = {u.total_tokens}"

        seed_chars, runtime_chars, seed_pairs = _split_message_stats(snap, meta)

        if meta.seed_count:
            chat_msgs = max(0, snap.messages_count - meta.seed_count)
            msg_breakdown = f"种子 {meta.seed_count} + 聊天 {chat_msgs}"
        else:
            msg_breakdown = f"全部 {snap.messages_count} 条均为当轮对话"
        self._set("stat_messages", str(snap.messages_count))
        self._set("st_msg_breakdown", msg_breakdown)
        self._set("stat_rounds", str(snap.round))
        self._set("stat_tokens", str(snap.cumulative_total_tokens))

        self._set("ver_label", meta.version_label)

        if meta.few_shot is None:
            self._set_badge("v1 最小 Agent", C_STAT_ROUNDS, "#ffffff")
            self._set("ver_structure", "无 system / Few-shot")
            self._set("ver_seed", "0（首轮从空列表开始）")
            self._set("ver_role", "—")
            self._set("ver_role_src", "—")
            self._set("ver_route_reason", "—")
        elif meta.few_shot:
            if _is_v4(meta.version_id):
                badge = "v4 · ToT + CoT" if meta.tot_enabled else "v4 · CoT + Few-shot"
            elif _is_v3(meta.version_id):
                badge = "v3 · Few-shot"
            else:
                badge = "Few-shot 开启"
            self._set_badge(badge, C_SUCCESS_BG, C_SUCCESS)
            base = "system + 范例对已注入"
            if _is_v4(meta.version_id):
                base += " + CoT 格式" + (" + ToT 比选" if meta.tot_enabled else "")
            self._set("ver_structure", base)
            self._set("ver_seed", f"{meta.seed_count} 条（清空会话后保留）")
        else:
            if _is_v4(meta.version_id):
                badge = "v4 · CoT Zero-shot"
            elif _is_v3(meta.version_id):
                badge = "v3 · Zero-shot"
            else:
                badge = "Zero-shot"
            self._set_badge(badge, C_WARN_BG, C_WARN)
            base = "仅 system，无范例"
            if _is_v4(meta.version_id):
                base += " + CoT 格式" + (" + ToT 比选" if meta.tot_enabled else "")
            self._set("ver_structure", base)
            self._set("ver_seed", f"{meta.seed_count} 条（仅 system）")

        if _is_v3(meta.version_id) or _is_v4(meta.version_id) or _is_v6(
            meta.version_id
        ) or _is_v7(meta.version_id):
            if meta.role_id:
                name = meta.role_display_name or meta.role_id
                ver = f" · v{meta.role_version}" if meta.role_version else ""
                self._set("ver_role", f"{name} ({meta.role_id}{ver})")
            else:
                self._set("ver_role", "（待首句确定）")
            self._set("ver_role_src", meta.role_source or "—")
            if meta.route_reason:
                self._set("ver_route_reason", meta.route_reason)
            elif meta.role_source == "指定":
                self._set("ver_route_reason", "—（指定选角无路由依据）")
            elif meta.role_source == "待路由":
                self._set("ver_route_reason", "—（首条 user 后生成）")
            else:
                self._set("ver_route_reason", "—")
        elif meta.few_shot is not None:
            self._set("ver_role", "—")
            self._set("ver_role_src", "—")
            self._set("ver_route_reason", "—")

        if _is_v6(meta.version_id) or _is_v7(meta.version_id):
            if _is_v7(meta.version_id):
                self._set_badge("v7 · 读写 + done", C_SUCCESS_BG, C_SUCCESS)
                self._set(
                    "ver_structure",
                    "system + Few-shot + CoT + ReAct + read/list/write + done",
                )
                self._set(
                    "react_tools",
                    "calculator, read_file, list_dir, write_text, done",
                )
            else:
                self._set_badge("v6 · ReAct", C_SUCCESS_BG, C_SUCCESS)
                self._set(
                    "ver_structure",
                    "system + Few-shot + CoT + ReAct + calculator",
                )
                self._set("react_tools", "calculator")
            if session and _is_commercial_react_session(session):
                wp = getattr(session, "workspace_path", None)
                self._set(
                    "react_workspace",
                    str(wp) if wp and _is_v7(meta.version_id) else "—",
                )
                if session.react_steps_used or session.last_tool_steps:
                    self._set(
                        "react_steps",
                        f"{session.react_steps_used} 轮 LLM，工具 {len(session.last_tool_steps)} 次",
                    )
                    if _is_v7(meta.version_id):
                        done = session.last_done_ok
                        if done is True:
                            self._set("react_done", "通过", fg=C_SUCCESS)
                        elif done is False:
                            self._set("react_done", "未通过", fg=C_ERROR)
                        else:
                            self._set("react_done", "本轮未调用")
                    else:
                        self._set("react_done", "—")
                else:
                    self._set("react_steps", "—（发消息后显示）")
                    self._set("react_done", "—")
            else:
                self._set("react_workspace", "—")
                self._set("react_steps", "—")
                self._set("react_done", "—")
        else:
            self._set("react_tools", "—")
            self._set("react_workspace", "—")
            self._set("react_steps", "—")
            self._set("react_done", "—")

        self._set("cfg_model", cfg.model)
        self._set("cfg_url", cfg.base_url)
        self._set("cfg_temp", temp)
        self._set("cfg_maxtok", max_tok)
        self._set("cfg_key", key_hint, fg=key_color)
        self._set("st_rounds", str(snap.round))
        if meta.seed_count:
            pair_hint = f"，含 {seed_pairs} 组 Few-shot 范例" if seed_pairs else ""
            self._set(
                "st_seed_chars",
                f"{seed_chars}（system + 范例{pair_hint}；粗估，非 Token）",
            )
        else:
            self._set("st_seed_chars", "0（v1 无种子）")
        self._set(
            "st_runtime_chars",
            f"{runtime_chars}（仅你发送消息后新增；粗估，非 Token）",
        )
        self._set("tok_round", tok_round)
        self._set(
            "tok_total",
            f"输入 {snap.cumulative_prompt_tokens} + 输出 "
            f"{snap.cumulative_completion_tokens} = {snap.cumulative_total_tokens}",
        )

    def show_error(self, text: str) -> None:
        for key in ("stat_messages", "stat_rounds", "stat_tokens"):
            self._set(key, "—")
        if self._error_label:
            self._error_label.configure(text=text)
            self._error_label.pack(fill=tk.X, pady=(0, 8))


class MechanismViewerApp:
    def __init__(
        self, root: tk.Tk, initial_version_id: str, *, profile: str = "viewer1"
    ) -> None:
        self.root = root
        self._profile = resolve_viewer_profile(profile)
        self._profile_cfg = VIEWER_PROFILES[self._profile]
        self._version_specs = versions_for_profile(self._profile)
        self._busy = False
        self._version_id = initial_version_id
        self.session: AgentSession | PromptAgentSession | None = None
        self.meta = ViewerMeta(
            version_id=initial_version_id,
            version_label=VERSION_BY_ID[initial_version_id].label,
            few_shot=None,
            seed_count=0,
            keeps_seed_on_reset=initial_version_id != "v1_minimal",
        )

        root.title(str(self._profile_cfg["title"]))
        root.configure(bg=C_BG)
        root.minsize(960, 640)
        root.geometry("1120x700")

        self._setup_styles()

        # —— 顶栏 ——
        header = tk.Frame(root, bg=C_HEADER, height=52)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        tk.Label(
            header,
            text="Agent 机制查看器",
            font=("Microsoft YaHei UI", 13, "bold"),
            fg=C_HEADER_TEXT,
            bg=C_HEADER,
        ).pack(side=tk.LEFT, padx=(16, 24), pady=10)

        ver_box = tk.Frame(header, bg=C_HEADER)
        ver_box.pack(side=tk.LEFT, pady=8)
        tk.Label(
            ver_box,
            text="版本",
            font=("Microsoft YaHei UI", 9),
            fg="#bfdbfe",
            bg=C_HEADER,
        ).pack(side=tk.LEFT, padx=(0, 8))
        self.version_var = tk.StringVar(value=VERSION_BY_ID[initial_version_id].label)
        self.version_combo = ttk.Combobox(
            ver_box,
            textvariable=self.version_var,
            values=[v.label for v in self._version_specs],
            state="readonly",
            width=32,
            font=("Microsoft YaHei UI", 9),
        )
        self.version_combo.pack(side=tk.LEFT)
        self.version_combo.bind("<<ComboboxSelected>>", self._on_version_combo)
        if len(self._version_specs) <= 1:
            ver_box.pack_forget()

        self.role_box = tk.Frame(header, bg=C_HEADER)
        tk.Label(
            self.role_box,
            text="角色",
            font=("Microsoft YaHei UI", 9),
            fg="#bfdbfe",
            bg=C_HEADER,
        ).pack(side=tk.LEFT, padx=(0, 8))
        self.role_var = tk.StringVar(value="teacher")
        self.role_combo = ttk.Combobox(
            self.role_box,
            textvariable=self.role_var,
            values=self._role_combo_values(),
            state="readonly",
            width=18,
            font=("Microsoft YaHei UI", 9),
        )
        self.role_combo.pack(side=tk.LEFT)
        self.role_combo.bind("<<ComboboxSelected>>", self._on_role_combo)

        self.hint_var = tk.StringVar()
        tk.Label(
            header,
            textvariable=self.hint_var,
            font=("Microsoft YaHei UI", 8),
            fg="#93c5fd",
            bg=C_HEADER,
        ).pack(side=tk.LEFT, padx=(16, 0))

        tk.Button(
            header,
            text="重载 Prompt",
            command=self._reload_prompts,
            font=("Microsoft YaHei UI", 8),
            fg=C_HEADER_TEXT,
            bg="#1d4ed8",
            activebackground="#1e3a8a",
            activeforeground=C_HEADER_TEXT,
            relief=tk.FLAT,
            padx=10,
            pady=2,
            cursor="hand2",
        ).pack(side=tk.RIGHT, padx=(0, 16))

        # —— 主区 ——
        paned = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left = tk.Frame(paned, bg=C_BG, padx=2, pady=2)
        paned.add(left, weight=3)

        chat_card = tk.Frame(
            left, bg=C_SURFACE, highlightbackground=C_BORDER, highlightthickness=1
        )
        chat_card.pack(fill=tk.BOTH, expand=True)

        chat_head = tk.Frame(chat_card, bg=C_SURFACE)
        chat_head.pack(fill=tk.X, padx=12, pady=(10, 0))
        tk.Label(
            chat_head,
            text="对话",
            font=("Microsoft YaHei UI", 11, "bold"),
            fg=C_TEXT,
            bg=C_SURFACE,
        ).pack(side=tk.LEFT)
        self.status_var = tk.StringVar(value="就绪")
        tk.Label(
            chat_head,
            textvariable=self.status_var,
            font=("Microsoft YaHei UI", 8),
            fg=C_MUTED,
            bg=C_SURFACE,
        ).pack(side=tk.RIGHT)

        chat_body = tk.Frame(chat_card, bg=C_SURFACE)
        chat_body.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)
        self.chat_log = scrolledtext.ScrolledText(
            chat_body,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Microsoft YaHei UI", 10),
            bg="#fafbfc",
            relief=tk.FLAT,
            padx=8,
            pady=8,
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=C_BORDER,
        )
        self.chat_log.pack(fill=tk.BOTH, expand=True)
        self._tag_config()

        input_bar = tk.Frame(chat_card, bg=C_SURFACE)
        input_bar.pack(fill=tk.X, padx=12, pady=(0, 12))
        self.input_var = tk.StringVar()
        self.input_entry = tk.Entry(
            input_bar,
            textvariable=self.input_var,
            font=("Microsoft YaHei UI", 10),
            relief=tk.FLAT,
            bg="#f8fafc",
            highlightthickness=1,
            highlightbackground=C_BORDER,
            highlightcolor=C_ACCENT,
        )
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 8))
        self.send_btn = tk.Button(
            input_bar,
            text="发送",
            command=self._on_send,
            font=("Microsoft YaHei UI", 9, "bold"),
            fg="#ffffff",
            bg=C_ACCENT,
            activebackground=C_ACCENT_HOVER,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=16,
            pady=6,
            cursor="hand2",
        )
        self.send_btn.pack(side=tk.LEFT)
        self.reset_btn = tk.Button(
            input_bar,
            text="清空会话",
            command=self._on_reset,
            font=("Microsoft YaHei UI", 9),
            fg=C_TEXT,
            bg="#e2e8f0",
            activebackground="#cbd5e1",
            relief=tk.FLAT,
            padx=12,
            pady=6,
            cursor="hand2",
        )
        self.reset_btn.pack(side=tk.LEFT, padx=(8, 0))
        self.input_entry.bind("<Return>", lambda _e: self._on_send())

        right = tk.Frame(paned, bg=C_BG, padx=2, pady=2)
        paned.add(right, weight=2)

        scope_wrap = tk.Frame(
            right, bg=C_SURFACE, highlightbackground=C_BORDER, highlightthickness=1
        )
        scope_wrap.pack(fill=tk.X, pady=(0, 6))
        self.history_bar = HistoryScopeBar(scope_wrap, on_change=self._on_history_scope_change)
        self.history_bar.pack(fill=tk.X)

        notebook = ttk.Notebook(right)
        notebook.pack(fill=tk.BOTH, expand=True)

        mech_frame = tk.Frame(notebook, bg=C_BG)
        role_frame = tk.Frame(notebook, bg=C_BG)
        reasoning_frame = tk.Frame(notebook, bg=C_BG)
        quality_frame = tk.Frame(notebook, bg=C_BG)
        tools_frame = tk.Frame(notebook, bg=C_BG)
        trajectory_frame = tk.Frame(notebook, bg=C_BG)
        json_frame = tk.Frame(notebook, bg=C_BG)
        raw_frame = tk.Frame(notebook, bg=C_BG)
        notebook.add(mech_frame, text="  机制面板  ")
        if self._profile_cfg["show_role_tab"]:
            notebook.add(role_frame, text="  角色设定  ")
        if self._profile_cfg["show_reasoning_tab"]:
            notebook.add(reasoning_frame, text="  推理与比选  ")
        if self._profile_cfg.get("show_quality_tab"):
            notebook.add(quality_frame, text="  质检与修订  ")
        if self._profile_cfg.get("show_tools_tab"):
            notebook.add(tools_frame, text="  工具与循环  ")
        if self._profile_cfg.get("show_trajectory_tab"):
            notebook.add(trajectory_frame, text="  运行轨迹  ")
        notebook.add(json_frame, text="  messages JSON  ")
        if self._profile_cfg["show_raw_tab"]:
            notebook.add(raw_frame, text="  API 原始报文  ")

        self.dashboard = MechanismDashboard(mech_frame)
        self.dashboard.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self.role_panel: RoleSettingPanel | None = None
        if self._profile_cfg["show_role_tab"]:
            self.role_panel = RoleSettingPanel(role_frame)
            self.role_panel.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self.reasoning_panel: ReasoningPanel | None = None
        if self._profile_cfg["show_reasoning_tab"]:
            self.reasoning_panel = ReasoningPanel(reasoning_frame)
            self.reasoning_panel.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self.quality_panel: QualityPanel | None = None
        if self._profile_cfg.get("show_quality_tab"):
            self.quality_panel = QualityPanel(quality_frame)
            self.quality_panel.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self.tools_panel: ToolsPanel | None = None
        if self._profile_cfg.get("show_tools_tab"):
            self.tools_panel = ToolsPanel(tools_frame)
            self.tools_panel.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self.trajectory_panel: TrajectoryPanel | None = None
        if self._profile_cfg.get("show_trajectory_tab"):
            self.trajectory_panel = TrajectoryPanel(trajectory_frame)
            self.trajectory_panel.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        json_wrap = tk.Frame(
            json_frame, bg=C_SURFACE, highlightbackground=C_BORDER, highlightthickness=1
        )
        json_wrap.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.json_text = scrolledtext.ScrolledText(
            json_wrap,
            wrap=tk.NONE,
            font=("Consolas", 9),
            state=tk.DISABLED,
            bg="#0f172a",
            fg="#e2e8f0",
            insertbackground="#e2e8f0",
            relief=tk.FLAT,
            padx=8,
            pady=8,
        )
        self.json_text.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self.raw_panel: RawApiPanel | None = None
        if self._profile_cfg["show_raw_tab"]:
            self.raw_panel = RawApiPanel(raw_frame)
            self.raw_panel.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self._last_panel_err: str | None = None
        self._load_version(initial_version_id, confirm=False)

    @staticmethod
    def _role_combo_values() -> list[str]:
        try:
            return list_role_ids() + ["auto"]
        except Exception:
            return ["teacher", "strict_reviewer", "auto"]

    def _current_role_choice(self) -> str:
        if self._version_id == "v3_auto":
            return "auto"
        if _is_role_agent(self._version_id):
            return self.role_var.get().strip() or "teacher"
        return "teacher"

    def _sync_role_combo_visibility(self) -> None:
        if not self._profile_cfg["show_role_tab"] or not _is_role_agent(self._version_id):
            self.role_box.pack_forget()
            return
        self.role_box.pack(side=tk.LEFT, padx=(16, 0), pady=8)
        if self._version_id == "v3_auto":
            self.role_var.set("auto")
            self.role_combo.configure(state=tk.DISABLED)
        else:
            self.role_combo.configure(state="readonly")
            if self.role_var.get() == "auto":
                self.role_var.set("teacher")

    def _on_role_combo(self, _event: Any = None) -> None:
        if not _is_role_agent(self._version_id) or self._version_id == "v3_auto":
            return
        if self._busy:
            messagebox.showwarning("请稍候", "正在请求模型，请完成后再切换角色。")
            return
        choice = self.role_var.get().strip()
        if isinstance(self.session, (RoleAgentSession, CotAgentSession)) and self.session.role_id == choice:
            return
        if self.session and self.session.round_count > 0:
            if not messagebox.askyesno("切换角色", "切换角色将清空当轮对话并重建固定前缀。继续？"):
                if isinstance(self.session, (RoleAgentSession, CotAgentSession)) and self.session.role_id:
                    self.role_var.set(self.session.role_id)
                return
        self._load_version(self._version_id, confirm=False, role_choice=choice)

    def _on_history_scope_change(self) -> None:
        if self.session is None:
            return
        self._refresh_data_views(self.session.snapshot(), self._last_panel_err)

    def _reload_prompts(self) -> None:
        if self._busy:
            messagebox.showwarning("请稍候", "正在请求模型，请稍后再重载。")
            return
        if self._version_id not in tuple(self._profile_cfg["version_ids"]) or self._version_id == "v1_minimal":
            messagebox.showinfo("重载 Prompt", "当前 Agent 版本无可重载的 prompts。")
            return
        if self.session and self.session.round_count > 0:
            if not messagebox.askyesno(
                "重载 Prompt",
                "将从磁盘重新读取 prompts/ 下文件并清空当轮对话（无需退出程序）。继续？",
            ):
                return
        self._load_version(self._version_id, confirm=False, role_choice=self._current_role_choice())
        self.status_var.set("已重载 Prompt 文件（无需重启）")

    def _setup_styles(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass
        style.configure("TNotebook", background=C_BG, borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            padding=[12, 6],
            font=("Microsoft YaHei UI", 9),
        )

    def _set_hint(self) -> None:
        self.hint_var.set(VERSION_BY_ID[self._version_id].hint)

    def _revert_combo(self) -> None:
        self.version_var.set(VERSION_BY_ID[self._version_id].label)

    def _on_version_combo(self, _event: Any = None) -> None:
        label = self.version_var.get().strip()
        new_id = LABEL_TO_ID.get(label)
        if not new_id or new_id == self._version_id:
            return
        if self._busy:
            messagebox.showwarning("请稍候", "正在请求模型，请完成后再切换版本。")
            self._revert_combo()
            return
        self._load_version(new_id, confirm=False, preserve_chat=True)
        self.status_var.set(f"已切换至 {VERSION_BY_ID[new_id].label}（无需重启）")

    def _load_version(
        self,
        version_id: str,
        *,
        confirm: bool,
        preserve_chat: bool = False,
        role_choice: str | None = None,
    ) -> None:
        prev_label = (
            VERSION_BY_ID[self._version_id].label
            if preserve_chat and self._version_id
            else None
        )
        if confirm and self.session and self.session.round_count > 0:
            if not messagebox.askyesno("切换 Agent 版本", "切换将清空当前对话，是否继续？"):
                self._revert_combo()
                return

        try:
            choice = role_choice if role_choice is not None else self._current_role_choice()
            session = build_session(version_id, role_choice=choice)
        except (RuntimeError, FileNotFoundError, ValueError) as e:
            self.session = None
            self._version_id = version_id
            self.meta = ViewerMeta(
                version_id=version_id,
                version_label=VERSION_BY_ID[version_id].label,
                few_shot=None if version_id == "v1_minimal" else version_id == "v2_fewshot",
                seed_count=0,
                keeps_seed_on_reset=version_id != "v1_minimal",
            )
            if preserve_chat and prev_label:
                self._append_version_divider(prev_label)
            else:
                self._clear_chat()
            self._set_controls_enabled(False)
            self._set_hint()
            self._sync_role_combo_visibility()
            self._refresh_panels(None, str(e))
            return

        self.session = session
        self._version_id = version_id
        self.meta = make_viewer_meta(version_id, session)
        self._sync_role_combo_visibility()
        if isinstance(session, (RoleAgentSession, CotAgentSession)) and session.role_id:
            self.role_var.set(session.role_id)
        elif version_id == "v3_auto":
            self.role_var.set("auto")
        self.history_bar.set_scope(SCOPE_CURRENT)
        if preserve_chat and prev_label:
            self._append_version_divider(prev_label)
        else:
            self._clear_chat()
        self._append_chat("system", startup_message(self.meta))
        self._set_controls_enabled(True)
        self._set_hint()
        self._refresh_panels(session.snapshot())
        self.status_var.set("就绪")
        self.input_entry.focus_set()

    def _clear_chat(self) -> None:
        self.chat_log.configure(state=tk.NORMAL)
        self.chat_log.delete("1.0", tk.END)
        self.chat_log.configure(state=tk.DISABLED)

    def _tag_config(self) -> None:
        base = tkfont.Font(font=self.chat_log.cget("font"))
        self.chat_log.tag_configure("user", foreground="#1d4ed8", font=base)
        self.chat_log.tag_configure("assistant", foreground="#166534", font=base)
        self.chat_log.tag_configure("error", foreground=C_ERROR, font=base)
        self.chat_log.tag_configure("system", foreground=C_MUTED, font=base)
        self.chat_log.tag_configure(
            "user_block", background=C_USER_BG, spacing1=6, spacing3=6, lmargin1=8, rmargin=48
        )
        self.chat_log.tag_configure(
            "assistant_block",
            background=C_ASSISTANT_BG,
            spacing1=6,
            spacing3=6,
            lmargin1=8,
            rmargin=48,
        )
        self.chat_log.tag_configure(
            "system_block",
            background=C_SYSTEM_BG,
            spacing1=4,
            spacing3=4,
            lmargin1=8,
            rmargin=8,
        )
        self.chat_log.tag_configure(
            "error_block", background=C_ERROR_BG, spacing1=6, spacing3=6, lmargin1=8
        )
        self.chat_log.tag_configure(
            "divider",
            foreground=C_MUTED,
            justify=tk.CENTER,
        )
        self.chat_log.tag_configure(
            "divider_block",
            spacing1=4,
            spacing3=4,
            lmargin1=8,
            rmargin=8,
        )

    def _append_version_divider(self, version_label: str) -> None:
        self.chat_log.configure(state=tk.NORMAL)
        self.chat_log.insert(
            tk.END,
            f"\n────── {version_label} ──────\n",
            ("divider", "divider_block"),
        )
        self.chat_log.configure(state=tk.DISABLED)
        self.chat_log.see(tk.END)

    def _append_chat(self, role: str, text: str) -> None:
        labels = {"user": "你", "assistant": "助手", "error": "错误", "system": "系统"}
        block_tags = {
            "user": "user_block",
            "assistant": "assistant_block",
            "system": "system_block",
            "error": "error_block",
        }
        label = labels.get(role, role)
        role_tag = role if role in labels else "system"
        block = block_tags.get(role, "system_block")

        self.chat_log.configure(state=tk.NORMAL)
        self.chat_log.insert(tk.END, f"\n{label}\n", (role_tag, block))
        self.chat_log.insert(tk.END, f"{text}\n", (role_tag, block))
        self.chat_log.configure(state=tk.DISABLED)
        self.chat_log.see(tk.END)

    def _set_json(self, content: str) -> None:
        self.json_text.configure(state=tk.NORMAL)
        self.json_text.delete("1.0", tk.END)
        self.json_text.insert(tk.END, content)
        self.json_text.configure(state=tk.DISABLED)

    def _refresh_data_views(
        self, snap: MechanismSnapshot | None, err: str | None = None
    ) -> None:
        scope = self.history_bar.get_scope()
        if snap is None and self.session is None:
            self._set_json("[]")
            if self.raw_panel:
                self.raw_panel.show_empty(err)
            return
        self._set_json(format_messages_for_scope(self.session, snap, scope))
        if self.raw_panel:
            self.raw_panel.update_scope(self.session, snap, scope, err)

    def _refresh_panels(self, snap: MechanismSnapshot | None, err: str | None = None) -> None:
        self._last_panel_err = err
        if self.session:
            self.history_bar.sync_rounds(len(self.session.turn_history))

        if err and snap is None:
            self.dashboard.show_error(err)
            if self.role_panel:
                self.role_panel.update_panel(self.meta, self.session)
            if self.reasoning_panel:
                self.reasoning_panel.update_panel(self.meta, self.session)
            if self.quality_panel:
                self.quality_panel.update_panel(self.meta, self.session)
            if self.tools_panel:
                self.tools_panel.update_panel(self.meta, self.session)
            if self.trajectory_panel:
                self.trajectory_panel.update_panel(self.meta, self.session)
            self._refresh_data_views(None, err)
            return
        if err:
            self.dashboard.show_error(err)
            if self.role_panel:
                self.role_panel.update_panel(self.meta, self.session)
            if self.reasoning_panel:
                self.reasoning_panel.update_panel(self.meta, self.session)
            if self.quality_panel:
                self.quality_panel.update_panel(self.meta, self.session)
            if self.tools_panel:
                self.tools_panel.update_panel(self.meta, self.session)
            if self.trajectory_panel:
                self.trajectory_panel.update_panel(self.meta, self.session)
            self._refresh_data_views(snap, err)
            return
        assert snap is not None
        self.dashboard.update_dashboard(snap, self.meta, self.session)
        if self.role_panel:
            self.role_panel.update_panel(self.meta, self.session)
        if self.reasoning_panel:
            self.reasoning_panel.update_panel(self.meta, self.session)
        if self.quality_panel:
            self.quality_panel.update_panel(self.meta, self.session)
        if self.tools_panel:
            self.tools_panel.update_panel(self.meta, self.session)
        if self.trajectory_panel:
            self.trajectory_panel.update_panel(self.meta, self.session)
        self._refresh_data_views(snap)

    def _set_controls_enabled(self, enabled: bool) -> None:
        state = tk.NORMAL if enabled else tk.DISABLED
        self.send_btn.configure(state=state)
        self.reset_btn.configure(state=state)
        self.input_entry.configure(state=state)
        combo_state = "readonly" if enabled else tk.DISABLED
        self.version_combo.configure(state=combo_state)

    def _on_send(self) -> None:
        if self.session is None or self._busy:
            return
        text = self.input_var.get().strip()
        if not text:
            return

        self.input_var.set("")
        self._append_chat("user", text)
        self._busy = True
        self._set_controls_enabled(False)
        self.status_var.set("正在请求模型…")

        def worker() -> None:
            try:
                reply, snap = self.session.chat(text)
                self.root.after(0, lambda: self._on_chat_ok(reply, snap))
            except Exception as e:
                snap = self.session.snapshot()
                err_msg = format_api_error(e, snap)
                self.session.record_failed_turn(err_msg)
                self.session.rollback_last_user()
                snap = self.session.snapshot()
                self.root.after(0, lambda: self._on_chat_err(err_msg))

        threading.Thread(target=worker, daemon=True).start()

    def _on_chat_ok(self, reply: str, snap: MechanismSnapshot) -> None:
        self._append_chat("assistant", reply)
        if isinstance(self.session, (RoleAgentSession, CotAgentSession)):
            prev_id = self.meta.role_id
            self.meta = make_viewer_meta(self._version_id, self.session)
            if self.session.role_id:
                self.role_var.set(self.session.role_id)
            if (
                self.session.round_count == 1
                and self.session.role_source == "auto"
                and self.session.role_id
                and prev_id is None
            ):
                name = self.session.role.display_name if self.session.role else self.session.role_id
                reason = self.session.route_reason or "—"
                self._append_chat(
                    "system",
                    f"[选角] auto → {self.session.role_id} ({name}) · {reason}",
                )
            if isinstance(self.session, CotAgentSession) and self.session.last_cot:
                r = self.session.last_cot.reasoning.strip()
                c = self.session.last_cot.conclusion.strip()
                if r or c:
                    self._append_chat(
                        "system",
                        f"[CoT] 推理段 {len(r)} 字 · 结论段 {len(c)} 字",
                    )
            if (
                isinstance(self.session, CotAgentSession)
                and self.session.tot_enabled
                and self.session.last_plans
            ):
                n = len(self.session.last_plans)
                sel = self.session.selected_plan or "—"
                self._append_chat("system", f"[ToT] 生成 {n} 个计划，选中: {sel}")
        elif _is_commercial_react_session(self.session):
            prev_id = self.meta.role_id
            self.meta = make_viewer_meta(self._version_id, self.session)
            if (
                self.session.round_count == 1
                and self.session.role_id
                and prev_id is None
            ):
                name = (
                    self.session.role.display_name
                    if self.session.role
                    else self.session.role_id
                )
                reason = self.session.route_reason or "—"
                self._append_chat(
                    "system",
                    f"[选角] → {self.session.role_id} ({name}) · {reason}",
                )
            n_tools = len(self.session.last_tool_steps)
            if n_tools:
                self._append_chat(
                    "system",
                    f"[ReAct] {self.session.react_steps_used} 轮 LLM，工具 {n_tools} 次",
                )
            if _is_v7(self._version_id) and self.session.last_done_ok is not None:
                done_txt = (
                    "通过"
                    if self.session.last_done_ok
                    else "未通过（见运行轨迹）"
                )
                self._append_chat("system", f"[done 验收] {done_txt}")
        self._refresh_panels(snap)
        self._finish_turn("就绪")

    def _on_chat_err(self, err: str) -> None:
        self._append_chat("error", err)
        if self.session:
            self._refresh_panels(self.session.snapshot())
        self._finish_turn("请求失败")

    def _finish_turn(self, status: str) -> None:
        self._busy = False
        self.status_var.set(status)
        if self.session is not None:
            self._set_controls_enabled(True)
            self.input_entry.focus_set()

    def _on_reset(self) -> None:
        if self.session is None or self._busy:
            return
        if self.meta.keeps_seed_on_reset:
            if _is_role_agent(self._version_id):
                msg = "确定清空当轮对话吗？（角色固定前缀会按当前选角保留；auto 模式回到待路由）"
            else:
                msg = "确定清空当轮对话吗？（system 与 Few-shot 种子会保留）"
        else:
            msg = "确定清空对话与 messages 吗？"
        if not messagebox.askyesno("清空会话", msg):
            return
        snap = self.session.reset()
        if isinstance(self.session, (RoleAgentSession, CotAgentSession)):
            self.meta = make_viewer_meta(self._version_id, self.session)
        self.history_bar.set_scope(SCOPE_CURRENT)
        self._clear_chat()
        if self.meta.keeps_seed_on_reset:
            self._append_chat("system", "当轮对话已清空，种子 messages 仍在右侧 JSON 中。")
        else:
            self._append_chat("system", "会话已清空。")
        self._refresh_panels(snap)


def main(
    default_version: str | None = None, *, profile: str | None = None
) -> None:
    prof = resolve_viewer_profile(profile)
    initial = resolve_default_version(default_version, profile=prof)

    root = tk.Tk()
    MechanismViewerApp(root, initial, profile=prof)
    root.mainloop()


if __name__ == "__main__":
    main()
