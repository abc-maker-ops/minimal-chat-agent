# -*- coding: utf-8 -*-
"""reasoning_v5 终端入口。"""
from __future__ import annotations

import os

from prompt_session import ReasoningV5Session, resolve_reasoning_mode


def _use_few_shot() -> bool:
    raw = os.getenv("USE_FEW_SHOT", "1").strip().lower()
    return raw not in {"0", "false", "no"}


_MODE_LABEL = {
    "cot": "思维链（Prompt 层，同 v4）",
    "tot": "简化思维树 + 思维链",
    "consistency": "自洽性（多样本投票，对标 Self-Consistency）",
    "graph": "并行汇总（fan-out/fan-in，对标 LangGraph 简化 GoT）",
}


def main() -> None:
    mode = resolve_reasoning_mode()
    try:
        session = ReasoningV5Session(include_few_shot=_use_few_shot(), reasoning_mode=mode)
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(e)
        return

    cfg = session.config
    print(f"reasoning_v5 已启动 — {_MODE_LABEL.get(mode, mode)}")
    print(f"模型: {cfg.model}")
    print(f"接口: {cfg.base_url}")
    print(f"Few-shot: {'开启' if session.include_few_shot else '关闭'}")
    print(f"REASONING_MODE: {mode}")
    if session.auto_pending:
        print("选角: auto（首条 user 自动路由）")
    else:
        print(f"角色: {session.role_label()} [{session.role_source_label()}]")
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
            if session.last_plans:
                print("  [思维树 候选计划]")
                for i, p in enumerate(session.last_plans, start=1):
                    mark = " ← 选中" if p == session.selected_plan else ""
                    print(f"    {i}. {p}{mark}")
                print(f"  [思维树 比选依据] {session.plan_select_reason}")
            if session.last_consistency:
                print(
                    f"  [自洽性] 一致率 {session.agreement_rate:.0%} "
                    f"（{session.last_consistency.winner_count}/{len(session.last_consistency.conclusions)}）"
                )
                for i, c in enumerate(session.last_consistency.conclusions, 1):
                    mark = " ← 众数" if c.strip() == session.consensus_conclusion.strip() else ""
                    print(f"    样本{i} 结论: {c[:80]}{mark}")
            if session.last_graph_branches:
                print("  [思维图 子题并行]")
                for i, b in enumerate(session.last_graph_branches, 1):
                    print(f"    {i}. {b.question}")
                    print(f"       → {b.answer[:100]}")
        except Exception as e:
            print(f"\n[错误] 调用失败: {e}\n")
            session.rollback_last_user()
            continue

        if session.last_cot:
            if session.cot_format_ok():
                print("  [思维链] 格式 OK")
            else:
                print("  [思维链] 警告：未检测到完整的 ## 推理 / ## 结论")
        if snap.last_usage is not None:
            u = snap.last_usage
            print(
                f"  [usage] 输入 {u.prompt_tokens} + 输出 {u.completion_tokens} "
                f"= 合计 {u.total_tokens} tokens"
            )
        print(f"\n助手: {reply}\n")


if __name__ == "__main__":
    main()
