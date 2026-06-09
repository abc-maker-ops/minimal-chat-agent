# -*- coding: utf-8 -*-
"""reasoning_v4 终端入口。"""
from __future__ import annotations

import os

from prompt_session import AUTO_ROLE, CotAgentSession, resolve_tot_enabled


def _use_few_shot() -> bool:
    raw = os.getenv("USE_FEW_SHOT", "1").strip().lower()
    return raw not in {"0", "false", "no"}


def main() -> None:
    include_few_shot = _use_few_shot()
    tot = resolve_tot_enabled()
    try:
        session = CotAgentSession(include_few_shot=include_few_shot, tot_enabled=tot)
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(e)
        return

    cfg = session.config
    print(
        "reasoning_v4 已启动（基于 v3 角色栈 + Prompt 层 CoT"
        + (" + 简化 ToT" if tot else "")
        + "）"
    )
    print(f"模型: {cfg.model}")
    print(f"接口: {cfg.base_url}")
    print(f"Few-shot: {'开启' if include_few_shot else '关闭'}")
    print(f"REASONING_MODE: {'tot（计划比选）' if tot else 'cot'}")
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
                print("  [ToT 候选计划]")
                for i, p in enumerate(session.last_plans, start=1):
                    mark = " ← 选中" if p == session.selected_plan else ""
                    print(f"    {i}. {p}{mark}")
                print(f"  [ToT 比选依据] {session.plan_select_reason}")
        except Exception as e:
            print(f"\n[错误] 调用失败: {e}\n")
            session.rollback_last_user()
            continue

        if session.last_cot:
            if session.cot_format_ok():
                print("  [CoT] 格式 OK（已解析 ## 推理 / ## 结论）")
            else:
                print("  [CoT] 警告：未检测到完整的 ## 推理 / ## 结论 分段")
        if snap.last_usage is not None:
            u = snap.last_usage
            print(
                f"  [usage] 输入 {u.prompt_tokens} + 输出 {u.completion_tokens} "
                f"= 合计 {u.total_tokens} tokens"
            )
        print(f"\n助手: {reply}\n")


if __name__ == "__main__":
    main()
