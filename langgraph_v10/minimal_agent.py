# langgraph_v10 终端入口 — LangChain + LangGraph 图编排
from __future__ import annotations

import sys

from prompt_session import LangGraphAgentSession


def main() -> None:
    try:
        session = LangGraphAgentSession()
    except Exception as exc:
        print(f"启动失败: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print("langgraph_v10 已启动 — LangChain + LangGraph 图编排")
    print(f"工作区：{session.workspace_path}")
    print("环境变量：MAX_REACT_STEPS、TOOL_CHOICE_FIRST、LANGGRAPH_CHECKPOINT=1")
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
            nodes = session.last_node_path
            if nodes:
                suffix += f"\n[节点路径：{' → '.join(nodes[:8])}]"
            print(f"\nAgent: {reply}{suffix}")
        except Exception as exc:
            print(f"\n[错误] {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
