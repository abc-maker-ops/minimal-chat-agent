# -*- coding: utf-8 -*-
"""system_prompt_v2 终端入口。"""
from __future__ import annotations

import os
import sys

from prompt_session import PromptAgentSession


def _use_few_shot() -> bool:
    raw = os.getenv("USE_FEW_SHOT", "1").strip().lower()
    return raw not in {"0", "false", "no"}


def main() -> None:
    include_few_shot = _use_few_shot()
    try:
        session = PromptAgentSession(include_few_shot=include_few_shot)
    except RuntimeError as e:
        print(e)
        return

    cfg = session.config
    seed = 1 + (len(session.messages) - 1) // 2 if include_few_shot else 0
    print("system_prompt_v2 已启动（system + 可选 Few-shot）")
    print(f"模型: {cfg.model}")
    print(f"接口: {cfg.base_url}")
    print(f"Few-shot 范例: {'开启' if include_few_shot else '关闭（Zero-shot 对比）'}")
    if include_few_shot and seed:
        print(f"启动时 messages 已含 system + {seed} 组 Few-shot 示范")
    print("输入 exit 退出\n")

    while True:
        user_input = input("你: ").strip()
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit", "q"}:
            print("再见。")
            break

        try:
            reply, snap = session.chat(user_input)
        except Exception as e:
            print(f"\n[错误] 调用失败: {e}\n")
            session.rollback_last_user()
            continue

        if snap.last_usage is not None:
            u = snap.last_usage
            print(
                f"  [usage] 输入 {u.prompt_tokens} + 输出 {u.completion_tokens} "
                f"= 合计 {u.total_tokens} tokens"
            )
        print(f"\n助手: {reply}\n")
        if os.getenv("DEBUG_MESSAGES", "").strip() in {"1", "true", "yes"}:
            print(f"  [debug] messages 条数: {snap.messages_count}\n")


if __name__ == "__main__":
    main()
