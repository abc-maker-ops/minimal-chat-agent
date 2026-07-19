# langgraph_v11 终端入口 — StructuredTool + 并行 + 人审/检查点
from __future__ import annotations

import sys

from prompt_session import LangGraphAgentSession


def main() -> None:
    try:
        session = LangGraphAgentSession()
    except Exception as exc:
        print(f"启动失败: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print("langgraph_v11 已启动 — LC 工具封装 + LG 并行/人审/检查点")
    print(f"工作区：{session.workspace_path}")
    print(
        "环境变量：MAX_REACT_STEPS、PARALLEL_TOOL_CALLS、"
        "LANGGRAPH_CHECKPOINT=1、HUMAN_GATE=1、AUTO_APPROVE=0"
    )
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
                suffix += f"\n[节点路径：{' → '.join(nodes[:10])}]"
            if session.last_parallel_group is not None:
                suffix += f"\n[最近并行组：{session.last_parallel_group}]"
            print(f"\nAgent: {reply}{suffix}")
        except Exception as exc:
            print(f"\n[错误] {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
