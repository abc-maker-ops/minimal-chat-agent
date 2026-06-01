# -*- coding: utf-8 -*-
"""role_setting_v3 终端入口。"""
from __future__ import annotations

import os
import sys

from prompt_session import AUTO_ROLE, RoleAgentSession, resolve_role_env


def _use_few_shot() -> bool:
    raw = os.getenv("USE_FEW_SHOT", "1").strip().lower()
    return raw not in {"0", "false", "no"}


def main() -> None:
    include_few_shot = _use_few_shot()
    try:
        session = RoleAgentSession(include_few_shot=include_few_shot)
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(e)
        return

    cfg = session.config
    env_role = resolve_role_env()
    print("role_setting_v3 已启动（角色文件 + 选角）")
    print(f"模型: {cfg.model}")
    print(f"接口: {cfg.base_url}")
    print(f"Few-shot: {'开启' if include_few_shot else '关闭'}")
    if session.auto_pending:
        print(f"选角: auto（首条 user 消息自动路由；可设 AGENT_ROLE={AUTO_ROLE}）")
    else:
        print(f"角色: {session.role_label()} [{session.role_source_label()}]")
        print(f"AGENT_ROLE={env_role}")
    if session.seed_count:
        print(f"固定前缀: {session.seed_count} 条 messages")
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
            if session.round_count == 1 and session.role_source == "auto":
                print(
                    f"  [选角] auto → {session.role_id} "
                    f"({session.role.display_name}) · {session.route_reason}"
                )
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
