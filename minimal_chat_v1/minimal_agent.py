# -*- coding: utf-8 -*-
"""
minimal_chat_v1：第 02 课最小 Agent。
- 维护 messages，循环调用 chat.completions
- 无 system（见 system_prompt_v2）
- 无工具 / ReAct / LangChain
"""
from __future__ import annotations

import os

from agent_session import AgentSession


def main() -> None:
    debug_messages = os.getenv("DEBUG_MESSAGES", "").strip() in {"1", "true", "yes"}

    try:
        session = AgentSession()
    except RuntimeError as e:
        print(e)
        return

    cfg = session.config
    print("minimal_chat_v1 已启动（智谱 GLM / OpenAI 兼容接口）")
    print(f"模型: {cfg.model}")
    print(f"接口: {cfg.base_url}")
    if cfg.temperature is not None:
        print(f"temperature: {cfg.temperature}")
    if cfg.max_tokens is not None:
        print(f"max_tokens: {cfg.max_tokens}")
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
        if debug_messages:
            print(f"  [debug] 当前 messages 条数: {snap.messages_count}\n")


if __name__ == "__main__":
    main()
