# -*- coding: utf-8 -*-
"""react_v6 smoke test（可 mock，无需 API）。"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

_LAB = Path(__file__).resolve().parent.parent
_RV6 = Path(__file__).resolve().parent
sys.path.insert(0, str(_LAB / "minimal_chat_v1"))
sys.path.insert(0, str(_RV6))

from calculator import eval_expression  # noqa: E402
from task_router import analyze_task  # noqa: E402


def test_calculator() -> None:
    assert eval_expression("23+19") == ("42", True)
    assert eval_expression("(10+5)*3") == ("45", True)
    assert not eval_expression("1/0")[1]
    print("calculator: OK")


def test_task_router() -> None:
    simple = analyze_task("1+1 等于几")
    assert not simple.use_tot
    assert not simple.use_refine
    deliver = analyze_task("请汇总三份文件并生成交付报告")
    assert deliver.use_tot and deliver.use_refine
    print("task_router: OK")


def test_react_mock() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("react_v6_ps", _RV6 / "prompt_session.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["react_v6_ps"] = mod
    spec.loader.exec_module(mod)
    CommercialAgentSession = mod.CommercialAgentSession

    queue: list[MagicMock] = []

    def _tool_msg(expr: str, cid: str) -> MagicMock:
        m = MagicMock()
        m.content = ""
        tc = MagicMock()
        tc.id = cid
        tc.type = "function"
        fn = MagicMock()
        fn.name = "calculator"
        fn.arguments = json.dumps({"expression": expr})
        tc.function = fn
        m.tool_calls = [tc]
        return m

    queue.append(_tool_msg("23+19", "c1"))
    queue.append(_tool_msg("42*2", "c2"))
    final = MagicMock()
    final.content = "## 推理\n先加后乘。\n## 结论\n84"
    final.tool_calls = []
    queue.append(final)

    def _create(**kwargs):
        msg = queue.pop(0)
        choice = MagicMock()
        choice.message = msg
        resp = MagicMock()
        resp.choices = [choice]
        usage = MagicMock()
        usage.prompt_tokens = 10
        usage.completion_tokens = 5
        usage.total_tokens = 15
        resp.usage = usage
        return resp

    os.environ["API_MIN_INTERVAL_SEC"] = "0"
    session = CommercialAgentSession()
    session.auto_pending = False
    session._apply_role("teacher", source="manual")
    session.client = MagicMock()
    session.client.chat.completions.create.side_effect = _create
    reply, _ = session.chat("先算 23+19，再乘以 2，给出最终数字。")
    assert len(session.last_tool_steps) == 2
    assert session.runtime_trace is not None
    assert "ReAct" in session.runtime_trace.as_text()
    assert "84" in reply
    print("react mock: OK", f"tools={len(session.last_tool_steps)}")


if __name__ == "__main__":
    test_calculator()
    test_task_router()
    test_react_mock()
