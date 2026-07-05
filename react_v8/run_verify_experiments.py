# -*- coding: utf-8 -*-
"""一次性跑第 09 篇实验 1–3 并打印必验项（需 ZHIPU_API_KEY）。"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))

from prompt_session import ToolEngineeredAgentSession  # noqa: E402
from task_router import TaskRoute  # noqa: E402

# 实验只验 ReAct 主路径，关闭 ToT / 精炼旁路以缩短 API 轮次
import prompt_session as _ps  # noqa: E402

_ps.analyze_task = lambda _t: TaskRoute(False, False, "", "")

PROMPT_EXP1 = (
    "并行读取 input/note_a.txt、input/note_b.txt、input/note_c.txt，"
    "汇总写入 output/summary.md（含 ## 结论），再 done 验收，"
    "format=markdown，required_headings 含 ## 结论。"
)
PROMPT_EXP2 = (
    "写 output/draft.md，正文只有 ## 推理、不要 ## 结论，"
    "done 验收 required_headings 含 ## 结论；若 ok 为 false 则补写后再 done。"
)


def _clear_output() -> None:
    out = _ROOT / "workspace" / "output"
    for p in out.glob("*"):
        if p.is_file():
            p.unlink()


def _summarize(session: ToolEngineeredAgentSession, name: str) -> dict:
    reads = [s for s in session.last_tool_steps if s.tool_name == "read_file"]
    read_groups = {s.parallel_group for s in reads if s.parallel_group is not None}
    done_calls = [s for s in session.last_tool_steps if s.tool_name == "done"]
    read_errors = [
        s for s in reads if s.observation.startswith("错误：") or not s.ok
    ]
    policies = " → ".join(session.last_tool_policies)
    forced = any("forced" in p.lower() or "done" in p.lower() for p in session.last_tool_policies[1:])
    return {
        "name": name,
        "done_ok": session.last_done_ok,
        "parallel_batches": session.parallel_batch_count,
        "read_file_count": len(reads),
        "read_parallel_groups": sorted(g for g in read_groups if g is not None),
        "read_errors": len(read_errors),
        "done_call_count": len(done_calls),
        "tool_policy_summary": policies,
        "has_forced_done_label": "force" in policies.lower() or any(
            "forced" in p.lower() for p in session.last_tool_policies
        ),
        "first_policy": session.last_tool_policies[0] if session.last_tool_policies else "",
    }


def _run(name: str, prompt: str, **env_overrides: str) -> dict:
    saved = {k: os.environ.get(k) for k in env_overrides}
    for k, v in env_overrides.items():
        os.environ[k] = v
    _clear_output()
    session = ToolEngineeredAgentSession()
    session.auto_pending = False
    session._apply_role("teacher", source="manual")
    print(f"\n=== {name} ===", flush=True)
    print(f"prompt: {prompt[:60]}…", flush=True)
    reply, _ = session.chat(prompt)
    print(f"reply 摘要: {reply[:120]}…" if len(reply) > 120 else f"reply: {reply}", flush=True)
    result = _summarize(session, name)
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    return result


def main() -> None:
    os.environ.setdefault("API_MIN_INTERVAL_SEC", "1")
    os.environ["TOOL_SCHEMA_PROFILE"] = "good"
    os.environ["TOOL_CHOICE_FIRST"] = "required"
    os.environ["PARALLEL_TOOL_CALLS"] = "1"
    os.environ["FORCE_DONE_ON_TEXT_EXIT"] = "1"

    r1 = _run("实验1 Parallel+done", PROMPT_EXP1)
    r2 = _run("实验2 Forced done", PROMPT_EXP2)
    r3 = _run(
        "实验3 legacy Schema",
        PROMPT_EXP1,
        TOOL_SCHEMA_PROFILE="legacy",
    )

    checks = {
        "实验1_done_ok": r1["done_ok"] is True,
        "实验1_reads": r1["read_file_count"] >= 3,
        "实验1_parallel_可变": r1["parallel_batches"] >= 1
        or len(r1["read_parallel_groups"]) >= 1,
        "实验2_done_twice": r2["done_call_count"] >= 2,
        "实验2_done_ok": r2["done_ok"] is True,
        "实验3_reads_ok": r3["read_file_count"] >= 1 and r3["read_errors"] == 0,
        "实验3_done_ok": r3["done_ok"] is True,
    }

    print("\n=== 必验项汇总 ===", flush=True)
    print(json.dumps({**checks, "r1": r1, "r2": r2, "r3": r3}, ensure_ascii=False, indent=2))
    required = [
        checks["实验1_done_ok"],
        checks["实验1_reads"],
        checks["实验2_done_twice"],
        checks["实验2_done_ok"],
        checks["实验3_reads_ok"],
        checks["实验3_done_ok"],
    ]
    if not all(required):
        raise SystemExit(1)
    if not checks["实验1_parallel_可变"]:
        print("\n[提示] 实验1 未出现并行组，属模型分轮读取的可变项，见文章 6.5 节。", flush=True)
    print("\nall required live experiment checks passed", flush=True)


if __name__ == "__main__":
    main()
