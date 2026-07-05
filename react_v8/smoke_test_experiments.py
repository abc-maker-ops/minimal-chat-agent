# -*- coding: utf-8 -*-
"""react_v8 smoke test（可 mock，无需 API）。"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

_LAB = Path(__file__).resolve().parent.parent
_RV8 = Path(__file__).resolve().parent
sys.path.insert(0, str(_LAB / "minimal_chat_v1"))
sys.path.insert(0, str(_RV8))

from parallel_runner import can_run_parallel, execute_tool_calls  # noqa: E402
from task_router import TaskRoute  # noqa: E402
from tool_policy import ReactContext, resolve_tool_policy, should_force_done_after_text_exit  # noqa: E402
from tool_registry import run_tool, validate_tool_args  # noqa: E402


def test_parallel_safe() -> None:
    assert can_run_parallel(["read_file", "read_file"])
    assert not can_run_parallel(["read_file", "write_text"])
    print("parallel safe: OK")


def test_tool_policy() -> None:
    p0 = resolve_tool_policy(ReactContext(0, False, None))
    assert p0.tool_choice == "required"
    p_auto = resolve_tool_policy(ReactContext(2, True, None))
    assert p_auto.tool_choice == "auto"
    forced = resolve_tool_policy(ReactContext(1, True, False), force_done=True)
    assert forced.tool_choice["function"]["name"] == "done"
    assert should_force_done_after_text_exit(
        ReactContext(3, True, False, user_requires_done=True)
    )
    print("tool_policy: OK")


def test_schema_validate() -> None:
    err = validate_tool_args("write_text", {"path": "draft.md", "content": "x"})
    assert err and "output/" in err
    err2 = validate_tool_args("read_file", {"path": "../etc/passwd"})
    assert err2
    print("schema validate: OK")


def test_parallel_execute() -> None:
    calls = []
    for i, path in enumerate(["input/note_a.txt", "input/note_b.txt"], start=1):
        tc = MagicMock()
        tc.id = f"c{i}"
        fn = MagicMock()
        fn.name = "read_file"
        fn.arguments = json.dumps({"path": path})
        tc.function = fn
        calls.append(tc)

    def ok(obs: str, name: str) -> bool:
        return not obs.startswith("错误：")

    batch = execute_tool_calls(
        calls, run_tool, ok, parallel=True, react_round=0, start_step=1
    )
    assert len(batch) == 2
    assert batch[0][4] == batch[1][4] == 1
    print("parallel execute: OK")


def test_react_mock_parallel_and_force_done() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("react_v8_ps", _RV8 / "prompt_session.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["react_v8_ps"] = mod
    spec.loader.exec_module(mod)
    ToolEngineeredAgentSession = mod.ToolEngineeredAgentSession

    queue: list[MagicMock] = []

    def _parallel_reads() -> MagicMock:
        m = MagicMock()
        m.content = ""
        tcs = []
        for i, p in enumerate(["input/note_a.txt", "input/note_b.txt"], start=1):
            tc = MagicMock()
            tc.id = f"r{i}"
            tc.type = "function"
            fn = MagicMock()
            fn.name = "read_file"
            fn.arguments = json.dumps({"path": p})
            tc.function = fn
            tcs.append(tc)
        m.tool_calls = tcs
        return m

    def _write_msg() -> MagicMock:
        m = MagicMock()
        m.content = ""
        tc = MagicMock()
        tc.id = "w1"
        tc.type = "function"
        fn = MagicMock()
        fn.name = "write_text"
        fn.arguments = json.dumps(
            {
                "path": "output/summary.md",
                "content": "# 汇总\n\n## 结论\n测试",
            }
        )
        tc.function = fn
        m.tool_calls = [tc]
        return m

    text_exit = MagicMock()
    text_exit.content = "已完成，请查收。"
    text_exit.tool_calls = []

    def _done_msg() -> MagicMock:
        m = MagicMock()
        m.content = ""
        tc = MagicMock()
        tc.id = "d1"
        tc.type = "function"
        fn = MagicMock()
        fn.name = "done"
        fn.arguments = json.dumps(
            {
                "path": "output/summary.md",
                "format": "markdown",
                "required_headings": ["## 结论"],
            }
        )
        tc.function = fn
        m.tool_calls = [tc]
        return m

    final = MagicMock()
    final.content = "## 推理\n…\n## 结论\n完成"
    final.tool_calls = []

    queue.extend([_parallel_reads(), _write_msg(), text_exit, _done_msg(), final])

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
    os.environ["FORCE_DONE_ON_TEXT_EXIT"] = "1"
    session = ToolEngineeredAgentSession()
    session.auto_pending = False
    session._apply_role("teacher", source="manual")
    mod.analyze_task = lambda _t: TaskRoute(False, False, "", "")
    session.client = MagicMock()
    session.client.chat.completions.create.side_effect = _create
    user = (
        "并行读取 input/note_a.txt 与 input/note_b.txt，"
        "写入 output/summary.md（含 ## 结论），调用 done 验收。"
    )
    reply, _ = session.chat(user)
    assert session.parallel_batch_count >= 1
    assert session.last_done_ok is True
    assert len(session.last_tool_steps) >= 4
    assert "required" in session.last_tool_policies[0]
    print("react mock:", f"tools={len(session.last_tool_steps)}", f"parallel={session.parallel_batch_count}")


if __name__ == "__main__":
    test_parallel_safe()
    test_tool_policy()
    test_schema_validate()
    test_parallel_execute()
    test_react_mock_parallel_and_force_done()
    print("all smoke tests passed")
