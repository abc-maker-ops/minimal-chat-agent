# -*- coding: utf-8 -*-
"""langgraph_v11 冒烟测试（mock LLM，无需 API）。"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

_LAB = Path(__file__).resolve().parent.parent
_V11 = Path(__file__).resolve().parent
sys.path.insert(0, str(_LAB / "minimal_chat_v1"))
sys.path.insert(0, str(_V11))

os.environ["AGENT_WORKSPACE"] = str(_V11 / "workspace")
os.environ["API_MIN_INTERVAL_SEC"] = "0"
os.environ["HUMAN_GATE"] = "0"
os.environ["AUTO_APPROVE"] = "1"
os.environ["PARALLEL_TOOL_CALLS"] = "1"

from bridge_v8 import TaskRoute  # noqa: E402
from graph_app import build_graph, run_graph  # noqa: E402
from lc_tools import LC_TOOLS, build_langchain_tools  # noqa: E402
from messages_util import dicts_to_lc  # noqa: E402
from nodes import tools_node  # noqa: E402
from state import AgentState  # noqa: E402


def test_lc_tools() -> None:
    tools = build_langchain_tools()
    names = {t.name for t in tools}
    assert "read_file" in names and "write_text" in names and "done" in names
    assert len(LC_TOOLS) >= 5
    print("lc StructuredTool:", sorted(names))


def test_graph_compile() -> None:
    app = build_graph(llm=MagicMock(), with_checkpoint=False)
    assert app is not None
    print("graph compile: OK")


def test_parallel_tools_node() -> None:
    from langchain_core.messages import AIMessage, HumanMessage

    state: AgentState = {
        "messages": [
            HumanMessage(content="读三个文件"),
            AIMessage(
                content="",
                tool_calls=[
                    {"id": "a", "name": "read_file", "args": {"path": "input/note_a.txt"}},
                    {"id": "b", "name": "read_file", "args": {"path": "input/note_b.txt"}},
                    {"id": "c", "name": "read_file", "args": {"path": "input/note_c.txt"}},
                ],
            ),
        ],
        "react_round": 1,
        "tool_steps": [],
        "has_written": False,
        "node_path": [],
    }
    out = tools_node(state)
    steps = out.get("tool_steps") or []
    assert len(steps) == 3
    groups = {s.parallel_group for s in steps}
    assert None not in groups
    assert all(s.ok for s in steps)
    print("parallel tools_node: group", steps[0].parallel_group)


def test_human_gate_interrupt() -> None:
    from langchain_core.messages import AIMessage

    os.environ["HUMAN_GATE"] = "1"
    os.environ["AUTO_APPROVE"] = "1"
    calls = {"n": 0}

    def fake_invoke(_messages, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "w1",
                        "name": "write_text",
                        "args": {
                            "path": "output/hitl.md",
                            "content": "## 结论\nok",
                        },
                    }
                ],
            )
        if calls["n"] == 2:
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "d1",
                        "name": "done",
                        "args": {
                            "path": "output/hitl.md",
                            "format": "markdown",
                            "required_headings": ["## 结论"],
                        },
                    }
                ],
            )
        return AIMessage(content="完成")

    llm = MagicMock()
    llm.bind_tools.return_value.invoke.side_effect = fake_invoke

    initial: AgentState = {
        "messages": dicts_to_lc(
            [{"role": "user", "content": "写 output/hitl.md 并 done"}]
        ),
        "has_written": False,
        "done_ok": None,
        "user_requires_done": True,
        "react_round": 0,
        "force_done_pending": False,
        "node_path": [],
        "policy_labels": [],
        "tool_steps": [],
        "pending_tool_names": [],
        "human_approved": None,
    }
    out = run_graph(
        initial,
        llm=llm,
        thread_id="smoke-hitl",
        with_checkpoint=True,
        approval_fn=lambda _p: True,
    )
    assert "human_gate" in (out.get("node_path") or [])
    assert out.get("has_written") is True
    os.environ["HUMAN_GATE"] = "0"
    print("human_gate interrupt: OK", " → ".join(out.get("node_path") or [])[:80])


def test_session_mock() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("lg_v11_ps", _V11 / "prompt_session.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["lg_v11_ps"] = mod
    spec.loader.exec_module(mod)
    LangGraphAgentSession = mod.LangGraphAgentSession
    mod.analyze_task = lambda _t: TaskRoute(False, False, "", "")

    with patch.object(mod, "run_graph") as mock_run:
        from langchain_core.messages import AIMessage

        mock_run.return_value = {
            "messages": [
                AIMessage(content="## 推理\na\n\n## 结论\nb"),
            ],
            "tool_steps": [],
            "done_ok": True,
            "policy_labels": ["R1:required"],
            "node_path": ["agent", "tools", "agent"],
            "react_round": 2,
            "last_parallel_group": 1,
        }
        s = LangGraphAgentSession(approval_fn=lambda _p: True)
        s.auto_pending = False
        s._apply_role("teacher", source="manual")
        reply, _ = s.chat("hello")
        assert "结论" in reply
        assert s.last_done_ok is True
    print("session mock: OK")


def main() -> None:
    test_lc_tools()
    test_graph_compile()
    test_parallel_tools_node()
    test_human_gate_interrupt()
    test_session_mock()
    print("all smoke tests passed")


if __name__ == "__main__":
    main()
