# -*- coding: utf-8 -*-
"""简化思维图：对标 LangGraph fan-out / fan-in — 分子题并行答，再汇总。"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "minimal_chat_v1"))
from api_resilience import create_chat_completion  # noqa: E402

MAX_BRANCHES = 3


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
        raise ValueError("子题列表必须是 JSON 数组")
    return data


@dataclass(frozen=True)
class GraphBranch:
    question: str
    answer: str


@dataclass(frozen=True)
class GraphRunResult:
    branches: tuple[GraphBranch, ...]
    merged_user: str


def decompose_subtasks(
    client: Any,
    *,
    model: str,
    system: str,
    user_task: str,
    max_branches: int = MAX_BRANCHES,
) -> list[str]:
    n = max(2, min(max_branches, MAX_BRANCHES))
    user_prompt = (
        f"将下面用户任务拆成 {n} 个可并行思考的子问题，彼此角度不同、互不重复。\n"
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
    questions = [str(q).strip() for q in items if str(q).strip()]
    if len(questions) < 2:
        raise ValueError(f"子题数不足 2 条，模型返回: {raw[:200]}")
    return questions[:n]


def answer_subtask(
    client: Any,
    *,
    model: str,
    system: str,
    sub_question: str,
) -> str:
    user_prompt = (
        f"请简洁回答下列子问题（2～4 句即可，不要分段标题）：\n\n{sub_question}"
    )
    resp = create_chat_completion(
        client,
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ],
    )
    return (resp.choices[0].message.content or "").strip()


def build_merge_user(user_task: str, branches: list[GraphBranch]) -> str:
    parts = [f"用户任务：{user_task}", "", "各子题并行结论："]
    for i, b in enumerate(branches, start=1):
        parts.append(f"{i}. 子题：{b.question}")
        parts.append(f"   结论：{b.answer}")
        parts.append("")
    parts.append(
        "请综合以上子题结论，按 ## 推理 / ## 结论 格式给出最终回答；"
        "推理段说明如何汇总，结论段给出可直接采用的答案。"
    )
    return "\n".join(parts).strip()


def run_graph_branches(
    client: Any,
    *,
    model: str,
    system: str,
    user_task: str,
) -> GraphRunResult:
    questions = decompose_subtasks(
        client, model=model, system=system, user_task=user_task
    )
    branches: list[GraphBranch] = []
    for q in questions:
        ans = answer_subtask(client, model=model, system=system, sub_question=q)
        branches.append(GraphBranch(question=q, answer=ans))
    merged = build_merge_user(user_task, branches)
    return GraphRunResult(branches=tuple(branches), merged_user=merged)
