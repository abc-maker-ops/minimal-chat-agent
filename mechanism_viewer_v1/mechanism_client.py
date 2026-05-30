# -*- coding: utf-8 -*-
"""
机制查看器（桌面 tkinter）：左侧对话，右侧机制仪表盘 / messages JSON。
窗口顶部可选择不同 Agent 版本（minimal_chat_v1、system_prompt_v2 等）。
"""
from __future__ import annotations

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

from agent_session import (  # noqa: E402
    DEFAULT_ZHIPU_BASE_URL,
    AgentSession,
    MechanismSnapshot,
    TurnRecord,
)
from prompt_session import PromptAgentSession  # noqa: E402

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
)
VERSION_BY_ID = {v.id: v for v in AGENT_VERSIONS}
LABEL_TO_ID = {v.label: v.id for v in AGENT_VERSIONS}


@dataclass
class ViewerMeta:
    version_id: str
    version_label: str
    few_shot: bool | None
    seed_count: int
    keeps_seed_on_reset: bool


def resolve_default_version(explicit: str | None = None) -> str:
    vid = (explicit or os.getenv("MECHANISM_AGENT_VERSION") or "v1_minimal").strip()
    if vid not in VERSION_BY_ID:
        return "v1_minimal"
    return vid


def build_session(version_id: str) -> AgentSession | PromptAgentSession:
    if version_id == "v1_minimal":
        return AgentSession()
    include_few_shot = version_id == "v2_fewshot"
    return PromptAgentSession(include_few_shot=include_few_shot)


def make_viewer_meta(version_id: str, session: AgentSession | PromptAgentSession) -> ViewerMeta:
    spec = VERSION_BY_ID[version_id]
    if version_id == "v1_minimal":
        return ViewerMeta(
            version_id=version_id,
            version_label=spec.label,
            few_shot=None,
            seed_count=0,
            keeps_seed_on_reset=False,
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
    head = f"第 {rec.round} 轮 · 发送 → LLM\n" + "─" * 40 + "\n\n"
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
    return f"已加载 {meta.version_label}；{fs}。种子 {meta.seed_count} 条，见右侧 JSON。"


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

    def update_dashboard(self, snap: MechanismSnapshot, meta: ViewerMeta) -> None:
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
        elif meta.few_shot:
            self._set_badge("Few-shot 开启", C_SUCCESS_BG, C_SUCCESS)
            self._set("ver_structure", "system + 范例对已注入")
            self._set("ver_seed", f"{meta.seed_count} 条（清空会话后保留）")
        else:
            self._set_badge("Zero-shot", C_WARN_BG, C_WARN)
            self._set("ver_structure", "仅 system，无范例")
            self._set("ver_seed", f"{meta.seed_count} 条（仅 system）")

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
    def __init__(self, root: tk.Tk, initial_version_id: str) -> None:
        self.root = root
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

        root.title("Agent 机制查看器")
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
            values=[v.label for v in AGENT_VERSIONS],
            state="readonly",
            width=32,
            font=("Microsoft YaHei UI", 9),
        )
        self.version_combo.pack(side=tk.LEFT)
        self.version_combo.bind("<<ComboboxSelected>>", self._on_version_combo)

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
        json_frame = tk.Frame(notebook, bg=C_BG)
        raw_frame = tk.Frame(notebook, bg=C_BG)
        notebook.add(mech_frame, text="  机制面板  ")
        notebook.add(json_frame, text="  messages JSON  ")
        notebook.add(raw_frame, text="  API 原始报文  ")

        self.dashboard = MechanismDashboard(mech_frame)
        self.dashboard.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

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

        self.raw_panel = RawApiPanel(raw_frame)
        self.raw_panel.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self._last_panel_err: str | None = None
        self._load_version(initial_version_id, confirm=False)

    def _on_history_scope_change(self) -> None:
        if self.session is None:
            return
        self._refresh_data_views(self.session.snapshot(), self._last_panel_err)

    def _reload_prompts(self) -> None:
        if self._busy:
            messagebox.showwarning("请稍候", "正在请求模型，请稍后再重载。")
            return
        if self._version_id not in ("v2_fewshot", "v2_zeroshot"):
            messagebox.showinfo(
                "重载 Prompt",
                "当前为第02篇版本，无 prompts 文件。\n"
                "切换到第03篇后可从 prompts/ 重新读取 system.txt、few_shot.json。",
            )
            return
        if self.session and self.session.round_count > 0:
            if not messagebox.askyesno(
                "重载 Prompt",
                "将从磁盘重新读取 prompts/ 下文件并清空当轮对话（无需退出程序）。继续？",
            ):
                return
        self._load_version(self._version_id, confirm=False)
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
        self, version_id: str, *, confirm: bool, preserve_chat: bool = False
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
            session = build_session(version_id)
        except RuntimeError as e:
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
            self._refresh_panels(None, str(e))
            return

        self.session = session
        self._version_id = version_id
        self.meta = make_viewer_meta(version_id, session)
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
            self.raw_panel.show_empty(err)
            return
        self._set_json(format_messages_for_scope(self.session, snap, scope))
        self.raw_panel.update_scope(self.session, snap, scope, err)

    def _refresh_panels(self, snap: MechanismSnapshot | None, err: str | None = None) -> None:
        self._last_panel_err = err
        if self.session:
            self.history_bar.sync_rounds(len(self.session.turn_history))

        if err and snap is None:
            self.dashboard.show_error(err)
            self._refresh_data_views(None, err)
            return
        if err:
            self.dashboard.show_error(err)
            self._refresh_data_views(snap, err)
            return
        assert snap is not None
        self.dashboard.update_dashboard(snap, self.meta)
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
            msg = "确定清空当轮对话吗？（system 与 Few-shot 种子会保留）"
        else:
            msg = "确定清空对话与 messages 吗？"
        if not messagebox.askyesno("清空会话", msg):
            return
        snap = self.session.reset()
        self.history_bar.set_scope(SCOPE_CURRENT)
        self._clear_chat()
        if self.meta.keeps_seed_on_reset:
            self._append_chat("system", "当轮对话已清空，种子 messages 仍在右侧 JSON 中。")
        else:
            self._append_chat("system", "会话已清空。")
        self._refresh_panels(snap)


def main(default_version: str | None = None) -> None:
    initial = resolve_default_version(default_version)

    root = tk.Tk()
    MechanismViewerApp(root, initial)
    root.mainloop()


if __name__ == "__main__":
    main()
