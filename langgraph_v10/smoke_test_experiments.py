# -*- coding: utf-8 -*-
"""langgraph_v10 冒烟测试（mock LLM，无需 API）。"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

_LAB = Path(__file__).resolve().parent.parent
_V10 = Path(__file__).resolve().parent
sys.path.insert(0, str(_LAB / "minimal_chat_v1"))
sys.path.insert(0, str(_V10))

from bridge_v8 import TaskRoute  # noqa: E402
from graph_app import build_graph, resolve_max_graph_steps  # noqa: E402
from messages_util import dicts_to_lc  # noqa: E402
from state import AgentState  # noqa: E402


def test_graph_compile() -> None:
    app = build_graph(llm=MagicMock(), with_checkpoint=False)
    assert app is not None
    print("graph compile: OK")


def test_tools_node_done_retry_mock() -> None:
    import prompt_session as ps

    ps.analyze_task = lambda _t: TaskRoute(False, False, "", "")

    from langchain_core.messages import AIMessage

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
                            "path": "output/draft.md",
                            "content": "## 推理\nonly",
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
                            "path": "output/draft.md",
                            "format": "markdown",
                            "required_headings": ["## 结论"],
                        },
                    }
                ],
            )
        if calls["n"] == 3:
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "w2",
                        "name": "write_text",
                        "args": {
                            "path": "output/draft.md",
                            "content": "## 推理\nx\n\n## 结论\ny",
                        },
                    }
                ],
            )
        if calls["n"] == 4:
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "d2",
                        "name": "done",
                        "args": {
                            "path": "output/draft.md",
                            "format": "markdown",
                            "required_headings": ["## 结论"],
                        },
                    }
                ],
            )
        return AIMessage(content="## 推理\nx\n\n## 结论\ny")

    llm = MagicMock()
    llm.bind_tools.return_value.invoke.side_effect = fake_invoke

    initial: AgentState = {
        "messages": dicts_to_lc(
            [{"role": "user", "content": "写 output/draft.md 并 done 验收"}]
        ),
        "has_written": False,
        "done_ok": None,
        "user_requires_done": True,
        "react_round": 0,
        "force_done_pending": False,
        "node_path": [],
        "policy_labels": [],
        "tool_steps": [],
    }
    os.environ["API_MIN_INTERVAL_SEC"] = "0"
    os.environ["AGENT_WORKSPACE"] = str(_V10 / "workspace")
    app = build_graph(llm=llm)
    out = app.invoke(initial, config={"recursion_limit": 20})
    assert out.get("done_ok") is True
    assert len(out.get("tool_steps") or []) >= 3
    assert "agent" in (out.get("node_path") or [])
    print("graph mock done retry:", len(out.get("tool_steps") or []), "tools")


def test_session_mock() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("lg_v10_ps", _V10 / "prompt_session.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["lg_v10_ps"] = mod
    spec.loader.exec_module(mod)
    LangGraphAgentSession = mod.LangGraphAgentSession
    mod.analyze_task = lambda _t: TaskRoute(False, False, "", "")

    with patch.object(mod, "run_graph") as mock_run:
        from langchain_core.messages import AIMessage

        mock_run.return_value = {
            "messages": [
                *dicts_to_lc([{"role": "user", "content": "hi"}]),
                AIMessage(content="## 推理\nok\n\n## 结论\ndone"),
            ],
            "tool_steps": [],
            "done_ok": True,
            "node_path": ["agent", "tools", "agent"],
            "policy_labels": ["R1:required（首轮须调工具）"],
            "react_round": 2,
        }
        session = LangGraphAgentSession()
        session.auto_pending = False
        session._apply_role("teacher", source="manual")
        reply, _ = session.chat("测试")
        assert session.last_done_ok is True
        assert "agent" in session.last_node_path
        print("session mock:", reply[:20])


if __name__ == "__main__":
    test_graph_compile()
    test_tools_node_done_retry_mock()
    test_session_mock()
    print("all smoke tests passed")
