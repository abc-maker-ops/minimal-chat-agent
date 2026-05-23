# -*- coding: utf-8 -*-
"""
mechanism_viewer_v1：桌面客户端（tkinter）。
左侧对话，右侧实时显示 messages 条数、Token、采样参数等机制关键值。
"""
from __future__ import annotations

import json
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

_LAB_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_LAB_ROOT / "minimal_chat_v1"))

from agent_session import (  # noqa: E402
    DEFAULT_ZHIPU_BASE_URL,
    AgentSession,
    MechanismSnapshot,
)


def format_mechanism_panel(snap: MechanismSnapshot) -> str:
    cfg = snap.config
    temp = "（模型默认）" if cfg.temperature is None else str(cfg.temperature)
    max_tok = "（模型默认）" if cfg.max_tokens is None else str(cfg.max_tokens)
    key_hint = "已设置" if cfg.api_key_set else "未检测到"

    if snap.last_usage is None:
        last_usage = "本轮：—（厂商未返回 usage）"
    else:
        u = snap.last_usage
        last_usage = (
            f"本轮：输入 {u.prompt_tokens} + 输出 {u.completion_tokens} "
            f"= 合计 {u.total_tokens} tokens"
        )

    return "\n".join(
        [
            "【运行配置】",
            f"  模型          {cfg.model}",
            f"  接口          {cfg.base_url}",
            f"  temperature   {temp}",
            f"  max_tokens    {max_tok}",
            f"  API Key       {key_hint}",
            "",
            "【对话状态 · 机制核心】",
            f"  已完成轮次    {snap.round}",
            f"  messages 条数 {snap.messages_count}  （每轮通常 +2：user + assistant）",
            f"  对话对数      {snap.user_assistant_pairs}",
            f"  正文约字符数  {snap.approx_chars_in_messages}  （粗估，非 Token）",
            "",
            "【Token · 计费】",
            f"  {last_usage}",
            (
                f"  累计：输入 {snap.cumulative_prompt_tokens} + 输出 "
                f"{snap.cumulative_completion_tokens} = 合计 "
                f"{snap.cumulative_total_tokens} tokens"
            ),
            "",
            "提示：下一轮请求的输入 Token 会随 messages 变长而上升。",
        ]
    )


def format_api_error(err: Exception, snap: MechanismSnapshot | None = None) -> str:
    msg = str(err).strip() or err.__class__.__name__
    lower = msg.lower()
    if "timed out" in lower or "timeout" in lower:
        base = snap.config.base_url if snap else DEFAULT_ZHIPU_BASE_URL
        return (
            f"请求超时：{msg}\n"
            "请检查：\n"
            f"  1. 机制面板「接口」应为 https://open.bigmodel.cn/api/paas/v4（当前 {base}）\n"
            "  2. 浏览器能否打开 open.bigmodel.cn\n"
            "  3. 仍慢可设环境变量 ZHIPU_TIMEOUT=180 后重启"
        )
    if "401" in msg or "authentication" in lower or ("invalid" in lower and "key" in lower):
        return f"鉴权失败：{msg}\n请确认 ZHIPU_API_KEY 正确且未过期。"
    return msg


def format_messages_json(snap: MechanismSnapshot) -> str:
    return json.dumps(snap.messages, ensure_ascii=False, indent=2)

class MechanismViewerApp:
    def __init__(self, root: tk.Tk, session: AgentSession | None) -> None:
        self.root = root
        self.session = session
        self._busy = False

        root.title("minimal_chat 机制查看器")
        root.minsize(900, 560)
        root.geometry("1024x640")

        paned = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # —— 左侧：对话 ——
        left = ttk.Frame(paned, padding=4)
        paned.add(left, weight=3)

        ttk.Label(left, text="对话", font=("Microsoft YaHei UI", 10, "bold")).pack(
            anchor=tk.W
        )
        self.chat_log = scrolledtext.ScrolledText(
            left, wrap=tk.WORD, state=tk.DISABLED, font=("Microsoft YaHei UI", 10)
        )
        self.chat_log.pack(fill=tk.BOTH, expand=True, pady=(4, 8))
        self._tag_config()

        input_row = ttk.Frame(left)
        input_row.pack(fill=tk.X)
        self.input_var = tk.StringVar()
        self.input_entry = ttk.Entry(input_row, textvariable=self.input_var)
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.send_btn = ttk.Button(input_row, text="发送", command=self._on_send)
        self.send_btn.pack(side=tk.LEFT)
        self.reset_btn = ttk.Button(input_row, text="清空会话", command=self._on_reset)
        self.reset_btn.pack(side=tk.LEFT, padx=(8, 0))

        self.input_entry.bind("<Return>", lambda _e: self._on_send())
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(left, textvariable=self.status_var).pack(anchor=tk.W, pady=(6, 0))

        # —— 右侧：机制 + JSON ——
        right = ttk.Frame(paned, padding=4)
        paned.add(right, weight=2)

        notebook = ttk.Notebook(right)
        notebook.pack(fill=tk.BOTH, expand=True)

        mech_frame = ttk.Frame(notebook, padding=4)
        json_frame = ttk.Frame(notebook, padding=4)
        notebook.add(mech_frame, text="机制面板")
        notebook.add(json_frame, text="messages JSON")

        self.mech_text = scrolledtext.ScrolledText(
            mech_frame,
            wrap=tk.WORD,
            font=("Consolas", 10),
            state=tk.DISABLED,
        )
        self.mech_text.pack(fill=tk.BOTH, expand=True)

        self.json_text = scrolledtext.ScrolledText(
            json_frame,
            wrap=tk.NONE,
            font=("Consolas", 9),
            state=tk.DISABLED,
        )
        self.json_text.pack(fill=tk.BOTH, expand=True)

        if session is None:
            self._set_controls_enabled(False)
            self._refresh_panels(None, "启动失败：未配置 ZHIPU_API_KEY")
        else:
            self._refresh_panels(session.snapshot())

    def _tag_config(self) -> None:
        self.chat_log.tag_configure("user", foreground="#1565C0")
        self.chat_log.tag_configure("assistant", foreground="#2E7D32")
        self.chat_log.tag_configure("error", foreground="#C62828")
        self.chat_log.tag_configure("system", foreground="#666666")

    def _append_chat(self, role: str, text: str) -> None:
        labels = {"user": "你", "assistant": "助手", "error": "错误", "system": "系统"}
        label = labels.get(role, role)
        tag = role if role in labels else "system"
        self.chat_log.configure(state=tk.NORMAL)
        self.chat_log.insert(tk.END, f"{label}: ", tag)
        self.chat_log.insert(tk.END, f"{text}\n\n", tag)
        self.chat_log.configure(state=tk.DISABLED)
        self.chat_log.see(tk.END)

    def _set_text(self, widget: scrolledtext.ScrolledText, content: str) -> None:
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, content)
        widget.configure(state=tk.DISABLED)

    def _refresh_panels(self, snap: MechanismSnapshot | None, err: str | None = None) -> None:
        if err:
            self._set_text(self.mech_text, err)
            self._set_text(self.json_text, "[]")
            return
        assert snap is not None
        self._set_text(self.mech_text, format_mechanism_panel(snap))
        self._set_text(self.json_text, format_messages_json(snap))

    def _set_controls_enabled(self, enabled: bool) -> None:
        state = tk.NORMAL if enabled else tk.DISABLED
        self.send_btn.configure(state=state)
        self.reset_btn.configure(state=state)
        self.input_entry.configure(state=state)

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
                self.session.rollback_last_user()
                snap = self.session.snapshot()
                self.root.after(
                    0, lambda: self._on_chat_err(format_api_error(e, snap))
                )

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
        if not messagebox.askyesno("清空会话", "确定清空对话与 messages 吗？"):
            return
        snap = self.session.reset()
        self.chat_log.configure(state=tk.NORMAL)
        self.chat_log.delete("1.0", tk.END)
        self.chat_log.configure(state=tk.DISABLED)
        self._append_chat("system", "会话已清空。")
        self._refresh_panels(snap)


def main() -> None:
    try:
        session = AgentSession()
    except RuntimeError as e:
        session = None
        startup_err = str(e)
    else:
        startup_err = None

    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except tk.TclError:
        pass

    app = MechanismViewerApp(root, session)
    if startup_err:
        messagebox.showerror("无法启动", startup_err)

    root.mainloop()


if __name__ == "__main__":
    main()
