# -*- coding: utf-8 -*-
"""reflection_v5 三项实验 smoke test（可 mock，无需 API）。"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

_LAB = Path(__file__).resolve().parent.parent
_RV5 = Path(__file__).resolve().parent
sys.path.insert(0, str(_LAB / "minimal_chat_v1"))
sys.path.insert(0, str(_LAB / "role_setting_v3"))
sys.path.insert(0, str(_LAB / "reasoning_v4"))
sys.path.insert(0, str(_RV5))

import importlib.util

_spec = importlib.util.spec_from_file_location("reflection_v5_prompt_session", _RV5 / "prompt_session.py")
if _spec is None or _spec.loader is None:
    raise ImportError("无法加载 reflection_v5/prompt_session.py")
_mod = importlib.util.module_from_spec(_spec)
sys.modules["reflection_v5_prompt_session"] = _mod
_spec.loader.exec_module(_mod)
ReflectionAgentSession = _mod.ReflectionAgentSession


def _mock_client(responses: list[str]) -> MagicMock:
    client = MagicMock()
    queue = list(responses)

    def _create(**kwargs):
        text = queue.pop(0)
        msg = MagicMock()
        msg.content = text
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

    client.chat.completions.create.side_effect = _create
    return client


COT_OK = """## 推理
步骤一。
## 结论
42"""


def test_exp1_consistency() -> None:
    os.environ["CONSISTENCY_SAMPLES"] = "3"
    session = ReflectionAgentSession(quality_mode="consistency", role_id="teacher")
    session.client = _mock_client([COT_OK, COT_OK, COT_OK.replace("42", "43")])
    reply, _ = session.chat("1+1=?")
    assert session.last_consistency is not None
    assert len(session.last_consistency.conclusions) == 3
    assert session.agreement_rate > 0
    assert "## 结论" in reply
    assert session.messages[-1]["role"] == "assistant"
    assert session.round_count == 1
    assert len(session.turn_history) == 3
    assert session._last_request is not None
    assert session._last_response is not None
    print("实验1 mock: OK", f"一致率={session.agreement_rate:.0%}")


def test_exp2_refine() -> None:
    draft = COT_OK.replace("42", "只有一点")
    critique = "- 漏项\n- 格式不完整"
    refined = COT_OK
    session = ReflectionAgentSession(quality_mode="refine", role_id="teacher")
    session.client = _mock_client([draft, critique, refined])
    reply, _ = session.chat("写三点总结")
    assert session.last_draft == draft
    assert session.last_critique == critique
    assert session.last_refined == refined
    assert session.cot_format_ok()
    assert reply == refined
    assert len(session.turn_history) == 3
    notes = [r.request.get("note") for r in session.turn_history]
    assert notes == ["draft", "self_critic", "refine"]
    assert session._last_request is not None
    print("实验2 mock: OK", "draft/critique/refined 均已写入会话字段")


def test_exp3_tot_refine() -> None:
    draft = COT_OK.replace("42", "草稿")
    critique = "- 需补全"
    refined = COT_OK
    session = ReflectionAgentSession(quality_mode="refine", tot_enabled=True, role_id="teacher")

    def _fake_tot(user_text: str) -> None:
        session.last_plans = ("先列提纲再写", "直接写")
        session.selected_plan = "先列提纲再写"
        session.plan_select_reason = "更清晰"

    session._run_tot = _fake_tot  # type: ignore[method-assign]
    session.client = _mock_client([draft, critique, refined])
    reply, _ = session.chat("规划并写800字科普")
    assert session.last_plans
    assert session.selected_plan
    assert session.last_critique
    assert session.last_refined == refined
    print("实验3 mock: OK", f"计划={session.selected_plan[:20]}...")


def test_viewer_session_build() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "viewer", _LAB / "mechanism_viewer_v1" / "mechanism_client.py"
    )
    assert spec and spec.loader
    # 仅验证 build_session 映射，不加载 tkinter 主窗口
    code = (_LAB / "mechanism_viewer_v1" / "mechanism_client.py").read_text(encoding="utf-8")
    assert "v5_refine_fewshot" in code
    assert "质检与修订" in code
    assert "QualityPanel" in code
    print("查看器代码: OK（含 QualityPanel 与 v5 版本条目）")


def test_live_api() -> None:
    if not (os.getenv("ZHIPU_API_KEY") or os.getenv("OPENAI_API_KEY")):
        print("真实 API 端到端: 跳过（无 Key）")
        return

    os.environ.setdefault("API_MIN_INTERVAL_SEC", "1.2")
    os.environ.setdefault("API_RETRY_MAX", "8")
    os.environ.setdefault("API_RETRY_BASE_SEC", "3")
    os.environ["CONSISTENCY_SAMPLES"] = "3"
    print("\n--- 实验1 真实 API（遇 429 自动退避重试）---")
    s1 = ReflectionAgentSession(quality_mode="consistency", role_id="teacher")
    r1, _ = s1.chat("23+19等于多少？只回答数字。")
    ok1 = s1.last_consistency is not None and len(s1.last_consistency.conclusions) == 3
    print(f"  一致率={s1.agreement_rate:.0%}", "字段OK" if ok1 else "FAIL", "结论片段:", r1[-80:])

    print("\n--- 实验2 真实 API ---")
    s2 = ReflectionAgentSession(quality_mode="refine", role_id="teacher")
    r2, _ = s2.chat("用三点总结 Agent 是什么；每点不超过15字。")
    ok2 = bool(s2.last_draft and s2.last_critique and s2.last_refined and s2.cot_format_ok())
    print(f"  draft={len(s2.last_draft)} critique={len(s2.last_critique)} refined={len(s2.last_refined)}", "OK" if ok2 else "FAIL")

    print("\n--- 实验3 真实 API ---")
    os.environ["REASONING_MODE"] = "tot"
    s3 = ReflectionAgentSession(quality_mode="refine", tot_enabled=True, role_id="teacher")
    r3, _ = s3.chat("帮我规划写一段100字左右的 Agent 入门介绍。")
    ok3 = bool(s3.last_plans and s3.selected_plan and s3.last_critique and s3.last_refined)
    print(f"  计划数={len(s3.last_plans)} 选中={s3.selected_plan[:40]}", "OK" if ok3 else "FAIL")

    if ok1 and ok2 and ok3:
        print("\n真实 API 三项实验: 均符合预期")
    else:
        raise SystemExit(1)


if __name__ == "__main__":
    test_exp1_consistency()
    test_exp2_refine()
    test_exp3_tot_refine()
    test_viewer_session_build()
    test_live_api()
