# -*- coding: utf-8 -*-
"""react_v6 终端入口 — 一体化运行机制，无需选模式。"""
from __future__ import annotations

import sys

from prompt_session import CommercialAgentSession


def main() -> None:
    try:
        session = CommercialAgentSession()
    except Exception as exc:
        print(f"启动失败: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print("react_v6 已启动 — 商用 Agent（一体化运行机制 + ReAct + calculator）")
    print("输入 quit 退出。")
    while True:
        try:
            user = input("\n你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见。")
            break
        if not user:
            continue
        if user.lower() in {"quit", "exit", "q"}:
            print("再见。")
            break
        try:
            reply, _ = session.chat(user)
            print(f"\nAgent: {reply}")
        except Exception as exc:
            print(f"\n[错误] {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
