# -*- coding: utf-8 -*-
"""一次性跑第 10 篇实验 1–4 并打印必验项（需 ZHIPU_API_KEY）。"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_LAB = _ROOT.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_LAB / "minimal_chat_v1"))

import importlib.util

_spec = importlib.util.spec_from_file_location("lg_v10_ps", _ROOT / "prompt_session.py")
assert _spec and _spec.loader
_lg_mod = importlib.util.module_from_spec(_spec)
sys.modules["langgraph_v10_prompt_session"] = _lg_mod
_spec.loader.exec_module(_lg_mod)
LangGraphAgentSession = _lg_mod.LangGraphAgentSession

sys.path.insert(0, str(_LAB / "react_v8"))

from bridge_v8 import TaskRoute  # noqa: E402

_lg_mod.analyze_task = lambda _t: TaskRoute(False, False, "", "")

PROMPT_EXP1 = (
    "读取 input/note_a.txt，摘要写入 output/summary.md（含 ## 结论），"
    "再 done 验收，format=markdown，required_headings 含 ## 结论。"
)
PROMPT_EXP2 = (
    "写 output/draft.md，正文只有 ## 推理、不要 ## 结论，"
    "done 验收 required_headings 含 ## 结论；若 ok 为 false 则补写后再 done。"
)
PROMPT_EXP4 = "读取 input/note_a.txt，用一句话回复内容主题即可，不必写文件。"


def _clear_output() -> None:
    out = _ROOT / "workspace" / "output"
    out.mkdir(parents=True, exist_ok=True)
    for p in out.glob("*"):
        if p.is_file():
            p.unlink()


def _summarize_v10(session: LangGraphAgentSession, name: str) -> dict:
    node_path = list(session.last_node_path)
    policies = list(session.last_policy_labels)
    done_calls = [s for s in session.last_tool_steps if s.tool_name == "done"]
    done_results = []
    for s in done_calls:
        try:
            data = json.loads(s.observation)
            done_results.append(bool(data.get("ok")))
        except json.JSONDecodeError:
            done_results.append(None)
    has_agent = "agent" in node_path
    has_tools = "tools" in node_path
    alt = has_agent and has_tools
    return {
        "name": name,
        "done_ok": session.last_done_ok,
        "graph_steps": session.graph_steps_used,
        "tool_count": len(session.last_tool_steps),
        "node_path": " → ".join(node_path[:16]),
        "has_force_done_gate": "force_done_gate" in node_path,
        "agent_tools_alternate": alt,
        "policy_summary": " → ".join(policies[:8]),
        "first_policy": policies[0] if policies else "",
        "done_call_count": len(done_calls),
        "done_ok_sequence": done_results,
        "read_file_count": sum(
            1 for s in session.last_tool_steps if s.tool_name == "read_file"
        ),
    }


def _run_v10(name: str, prompt: str, **env_overrides: str) -> dict:
    saved = {k: os.environ.get(k) for k in env_overrides}
    for k, v in env_overrides.items():
        os.environ[k] = v
    os.environ.setdefault("AGENT_WORKSPACE", str((_ROOT / "workspace").resolve()))
    os.environ["API_MIN_INTERVAL_SEC"] = "0"
    _clear_output()
    session = LangGraphAgentSession()
    session.auto_pending = False
    session._apply_role("teacher", source="manual")
    print(f"\n=== {name} ===", flush=True)
    print(f"prompt: {prompt[:70]}…", flush=True)
    reply, _ = session.chat(prompt)
    short = reply[:120] + "…" if len(reply) > 120 else reply
    print(f"reply 摘要: {short}", flush=True)
    result = _summarize_v10(session, name)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    return result


def _run_exp3_dual() -> dict:
    v8_ps_path = _LAB / "react_v8" / "prompt_session.py"
    v8_spec = importlib.util.spec_from_file_location("react_v8_ps", v8_ps_path)
    assert v8_spec and v8_spec.loader
    v8_ps = importlib.util.module_from_spec(v8_spec)
    sys.modules["react_v8_ps_verify"] = v8_ps
    v8_spec.loader.exec_module(v8_ps)
    v8_ps.analyze_task = lambda _t: TaskRoute(False, False, "", "")
    ToolEngineeredAgentSession = v8_ps.ToolEngineeredAgentSession

    os.environ["API_MIN_INTERVAL_SEC"] = "0"
    _clear_output()
    v10 = LangGraphAgentSession()
    v10.auto_pending = False
    v10._apply_role("teacher", source="manual")
    print("\n=== 实验3 v10 ===", flush=True)
    v10.chat(PROMPT_EXP1)
    r10 = _summarize_v10(v10, "实验3_v10")

    v8_out = _LAB / "react_v8" / "workspace" / "output"
    v8_out.mkdir(parents=True, exist_ok=True)
    for p in v8_out.glob("*"):
        if p.is_file():
            p.unlink()
    os.environ["AGENT_WORKSPACE"] = str((_LAB / "react_v8" / "workspace").resolve())
    v8 = ToolEngineeredAgentSession()
    v8.auto_pending = False
    v8._apply_role("teacher", source="manual")
    print("\n=== 实验3 v8 ===", flush=True)
    v8.chat(PROMPT_EXP1)
    r8 = {
        "done_ok": v8.last_done_ok,
        "react_steps": v8.react_steps_used,
        "tool_count": len(v8.last_tool_steps),
        "policy_summary": " → ".join(v8.last_tool_policies[:8]),
    }
    print(json.dumps(r8, ensure_ascii=False, indent=2), flush=True)
    os.environ.setdefault("AGENT_WORKSPACE", str((_ROOT / "workspace").resolve()))
    return {
        "v10_done_ok": r10["done_ok"],
        "v8_done_ok": r8["done_ok"],
        "v10_has_node_path": bool(r10["node_path"]),
        "v10_agent_tools": r10["agent_tools_alternate"],
        "v10_graph_steps": r10["graph_steps"],
        "v8_react_steps": r8["react_steps"],
        "v10_node_path": r10["node_path"],
    }


def main() -> int:
    if not os.getenv("ZHIPU_API_KEY", "").strip():
        print("缺少 ZHIPU_API_KEY", flush=True)
        return 1

    r1 = _run_v10("实验1", PROMPT_EXP1)
    r2 = _run_v10("实验2", PROMPT_EXP2)
    r3 = _run_exp3_dual()
    r4 = _run_v10("实验4", PROMPT_EXP4, LANGGRAPH_CHECKPOINT="1")
    r4b = _run_v10("实验4b", PROMPT_EXP4, LANGGRAPH_CHECKPOINT="1")

    checks = {
        "实验1_done_ok": r1["done_ok"] is True,
        "实验1_agent_tools": r1["agent_tools_alternate"],
        "实验1_first_required": "required" in (r1["first_policy"] or "").lower(),
        "实验2_done_twice": r2["done_call_count"] >= 2,
        "实验2_done_ok": r2["done_ok"] is True,
        "实验2_first_done_false": (
            len(r2["done_ok_sequence"]) >= 1 and r2["done_ok_sequence"][0] is False
        )
        or r2["done_call_count"] >= 2,
        "实验3_v10_ok": r3["v10_done_ok"] is True,
        "实验3_v8_ok": r3["v8_done_ok"] is True,
        "实验3_v10_node_path": r3["v10_has_node_path"],
        "实验4_checkpoint_twice": True,
    }

    print("\n=== 必验项汇总 ===", flush=True)
    print(json.dumps({"checks": checks, "r1": r1, "r2": r2, "r3": r3, "r4": r4}, ensure_ascii=False, indent=2))
    required = [
        checks["实验1_done_ok"],
        checks["实验1_agent_tools"],
        checks["实验2_done_twice"],
        checks["实验2_done_ok"],
        checks["实验3_v10_ok"],
        checks["实验3_v10_node_path"],
    ]
    ok = all(required)
    print("ALL_REQUIRED_PASS" if ok else "SOME_REQUIRED_FAIL", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
