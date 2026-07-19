# -*- coding: utf-8 -*-
"""第 11 篇实验 1–3 在线验证（需 ZHIPU_API_KEY）。"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_LAB = _ROOT.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_LAB / "minimal_chat_v1"))

os.environ.setdefault("AGENT_WORKSPACE", str((_ROOT / "workspace").resolve()))
os.environ["API_MIN_INTERVAL_SEC"] = os.environ.get("API_MIN_INTERVAL_SEC", "1")
os.environ["PARALLEL_TOOL_CALLS"] = "1"
os.environ["HUMAN_GATE"] = "0"
os.environ["AUTO_APPROVE"] = "1"

_spec = importlib.util.spec_from_file_location("lg_v11_ps", _ROOT / "prompt_session.py")
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
sys.modules["langgraph_v11_prompt_session"] = _mod
_spec.loader.exec_module(_mod)
LangGraphAgentSession = _mod.LangGraphAgentSession

from bridge_v8 import TaskRoute  # noqa: E402

_mod.analyze_task = lambda _t: TaskRoute(False, False, "", "")

PROMPT_EXP1 = (
    "读取 input/note_a.txt、input/note_b.txt、input/note_c.txt，"
    "汇总写入 output/summary.md（必须含 ## 结论），"
    "再 done 验收，format=markdown，required_headings 含 ## 结论。"
)
PROMPT_EXP2 = (
    "请在同一轮里并行读取 input/note_a.txt、input/note_b.txt、input/note_c.txt，"
    "不要分多轮各读一个；读完后写入 output/parallel_summary.md（含 ## 结论），"
    "再 done 验收，format=markdown，required_headings 含 ## 结论。"
)
PROMPT_EXP3 = (
    "将「## 结论\\n人工审批通过验证」写入 output/hitl_ok.md，"
    "再 done 验收，format=markdown，required_headings 含 ## 结论。"
)


def _clear_output() -> None:
    out = _ROOT / "workspace" / "output"
    out.mkdir(parents=True, exist_ok=True)
    for p in out.glob("*"):
        if p.is_file():
            p.unlink()


def _path_has_tools(node_path: tuple[str, ...]) -> bool:
    return any(n == "tools" or n.startswith("tools(") for n in node_path)


def _summarize(session: LangGraphAgentSession, name: str) -> dict:
    node_path = tuple(session.last_node_path)
    parallel_groups = {
        s.parallel_group
        for s in session.last_tool_steps
        if s.tool_name == "read_file" and s.parallel_group is not None
    }
    reads = [s for s in session.last_tool_steps if s.tool_name == "read_file"]
    return {
        "name": name,
        "done_ok": session.last_done_ok,
        "tool_count": len(session.last_tool_steps),
        "read_file_count": len(reads),
        "parallel_groups": sorted(parallel_groups),
        "last_parallel_group": session.last_parallel_group,
        "node_path": " → ".join(node_path[:20]),
        "has_agent": "agent" in node_path,
        "has_tools": _path_has_tools(node_path),
        "has_human_gate": "human_gate" in node_path,
        "policy": " → ".join(session.last_policy_labels[:8]),
    }


def _run(name: str, prompt: str, **env: str) -> dict:
    print(f"\n=== {name} ===", flush=True)
    for k, v in env.items():
        os.environ[k] = v
    _clear_output()
    session = LangGraphAgentSession(approval_fn=lambda _p: True)
    session.auto_pending = False
    session._apply_role("teacher", source="manual")
    reply, _ = session.chat(prompt)
    print(f"reply: {(reply or '')[:120]}…", flush=True)
    summary = _summarize(session, name)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return summary


def main() -> int:
    if not os.getenv("ZHIPU_API_KEY"):
        print("缺少 ZHIPU_API_KEY", file=sys.stderr)
        return 2

    # 实验 2 硬保证：同批三 read_file 的并行节点（不依赖模型采样）
    print("\n=== 实验2_并行节点冒烟（硬保证） ===", flush=True)
    smoke_spec = importlib.util.spec_from_file_location(
        "lg_v11_smoke", _ROOT / "smoke_test_experiments.py"
    )
    assert smoke_spec and smoke_spec.loader
    smoke_mod = importlib.util.module_from_spec(smoke_spec)
    smoke_spec.loader.exec_module(smoke_mod)
    smoke_mod.test_parallel_tools_node()
    parallel_smoke_ok = True

    r1 = _run(
        "实验1_StructuredTool主路径",
        PROMPT_EXP1,
        HUMAN_GATE="0",
        PARALLEL_TOOL_CALLS="1",
    )
    r2 = _run(
        "实验2_并行组_在线",
        PROMPT_EXP2,
        HUMAN_GATE="0",
        PARALLEL_TOOL_CALLS="1",
    )
    r3 = _run(
        "实验3_人工审批",
        PROMPT_EXP3,
        HUMAN_GATE="1",
        AUTO_APPROVE="1",
        LANGGRAPH_CHECKPOINT="1",
    )

    # 拒绝路径（不依赖模型采样）：固定审批 False
    print("\n=== 实验3b_人工审批拒绝 ===", flush=True)
    os.environ["HUMAN_GATE"] = "1"
    os.environ["AUTO_APPROVE"] = "0"
    _clear_output()
    session = LangGraphAgentSession(approval_fn=lambda _p: False)
    session.auto_pending = False
    session._apply_role("teacher", source="manual")
    session.chat(PROMPT_EXP3)
    hitl_path = Path(os.environ["AGENT_WORKSPACE"]) / "output" / "hitl_ok.md"
    reject_summary = {
        "has_human_gate": "human_gate" in session.last_node_path,
        "file_exists_after_reject": hitl_path.exists(),
        "node_path": " → ".join(session.last_node_path[:16]),
        "done_ok": session.last_done_ok,
    }
    print(json.dumps(reject_summary, ensure_ascii=False, indent=2), flush=True)

    online_parallel = bool(r2["parallel_groups"]) or "tools(parallel:" in r2["node_path"]
    checks = {
        "实验1_done_ok": r1["done_ok"] is True,
        "实验1_agent_tools": r1["has_agent"] and r1["has_tools"],
        "实验2_并行冒烟": parallel_smoke_ok,
        "实验2_在线_done_ok": r2["done_ok"] is True,
        "实验2_在线_出现并行组": online_parallel,
        "实验3_human_gate": r3["has_human_gate"] is True,
        "实验3_done_ok": r3["done_ok"] is True,
        "实验3b_human_gate": reject_summary["has_human_gate"] is True,
        "实验3b_拒绝未交付": (
            not reject_summary["file_exists_after_reject"]
            or reject_summary["done_ok"] is not True
        ),
    }

    print("\n=== 必验项汇总 ===", flush=True)
    print(json.dumps(checks, ensure_ascii=False, indent=2), flush=True)
    if not online_parallel:
        print(
            "说明：实验2在线未出现并行组（模型未同批返回≥2个只读 tool_calls）；"
            "并行节点能力以冒烟硬保证为准。",
            flush=True,
        )

    required = [
        checks["实验1_done_ok"],
        checks["实验1_agent_tools"],
        checks["实验2_并行冒烟"],
        checks["实验2_在线_done_ok"],
        checks["实验3_human_gate"],
        checks["实验3_done_ok"],
        checks["实验3b_human_gate"],
        checks["实验3b_拒绝未交付"],
    ]
    ok = all(required)
    print("RESULT:", "PASS" if ok else "FAIL", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
