# react_v7 终端入口 — 结构化交付 + done 验收
from __future__ import annotations

import sys

from prompt_session import DeliveryAgentSession


def main() -> None:
    try:
        session = DeliveryAgentSession()
    except Exception as exc:
        print(f"启动失败: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print("react_v7 已启动 — 商用 Agent（文件工具 + 结构化交付 + done 验收）")
    print(f"工作区：{session.workspace_path}")
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
            done = session.last_done_ok
            suffix = ""
            if done is True:
                suffix = "\n[done 验收：通过]"
            elif done is False:
                suffix = "\n[done 验收：未通过，见工具 Observation]"
            print(f"\nAgent: {reply}{suffix}")
        except Exception as exc:
            print(f"\n[错误] {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
