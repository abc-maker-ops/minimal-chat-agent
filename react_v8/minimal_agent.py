# react_v8 终端入口 — tool_choice / parallel / JSON Schema 工程化
from __future__ import annotations

import sys

from prompt_session import ToolEngineeredAgentSession


def main() -> None:
    try:
        session = ToolEngineeredAgentSession()
    except Exception as exc:
        print(f"启动失败: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print("react_v8 已启动 — 工具工程化（tool_choice / parallel / Schema）")
    print(f"工作区：{session.workspace_path}")
    print("环境变量：PARALLEL_TOOL_CALLS、TOOL_CHOICE_FIRST、TOOL_SCHEMA_PROFILE=legacy|good")
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
            parallel = session.parallel_batch_count
            if parallel:
                suffix += f"\n[并行批次数：{parallel}]"
            print(f"\nAgent: {reply}{suffix}")
        except Exception as exc:
            print(f"\n[错误] {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
