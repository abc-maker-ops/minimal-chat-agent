# -*- coding: utf-8 -*-
"""简化 ToT：2～3 条计划 → 评估选 1。"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "minimal_chat_v1"))
from api_resilience import create_chat_completion  # noqa: E402

MAX_PLANS = 3


def _extract_json_array(text: str) -> list[Any]:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("[")
    end = text.rfind("]")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("计划列表必须是 JSON 数组")
    return data


def propose_plans(
    client: Any,
    *,
    model: str,
    system: str,
    user_task: str,
    max_plans: int = MAX_PLANS,
) -> list[str]:
    n = max(2, min(max_plans, MAX_PLANS))
    user_prompt = (
        f"针对下面用户任务，给出 {n} 条互不相同的执行计划，每条 1～2 句。\n"
        f"只输出 JSON 数组，元素为字符串，不要 Markdown 代码块或其它说明。\n\n"
        f"用户任务：{user_task}"
    )
    resp = create_chat_completion(
        client,
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ],
    )
    raw = resp.choices[0].message.content or "[]"
    items = _extract_json_array(raw)
    plans = [str(p).strip() for p in items if str(p).strip()]
    if len(plans) < 2:
        raise ValueError(f"计划数不足 2 条，模型返回: {raw[:200]}")
    return plans[:n]


def select_plan(
    client: Any,
    *,
    model: str,
    user_task: str,
    plans: list[str],
) -> tuple[int, str]:
    numbered = "\n".join(f"{i + 1}. {p}" for i, p in enumerate(plans))
    user_prompt = (
        "你是任务规划评估器。根据用户任务，从下列计划中选最合适的一条。\n"
        "只输出 JSON 对象：{\"index\": 1 到 N 的整数, \"reason\": \"一句话理由\"}\n\n"
        f"用户任务：{user_task}\n\n计划列表：\n{numbered}"
    )
    resp = create_chat_completion(
        client,
        model=model,
        messages=[{"role": "user", "content": user_prompt}],
    )
    raw = resp.choices[0].message.content or "{}"
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("选计划结果必须是 JSON 对象")
    idx = int(data.get("index", 1)) - 1
    reason = str(data.get("reason", "")).strip() or "—"
    idx = max(0, min(idx, len(plans) - 1))
    return idx, reason
