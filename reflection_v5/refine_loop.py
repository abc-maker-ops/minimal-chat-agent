# -*- coding: utf-8 -*-
"""自我精炼：依据批评意见生成修订稿。"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "minimal_chat_v1"))
from api_resilience import create_chat_completion  # noqa: E402


def resolve_max_refine_rounds() -> int:
    raw = (os.getenv("MAX_REFINE_ROUNDS") or "2").strip()
    try:
        n = int(raw)
    except ValueError:
        n = 2
    return max(1, min(n, 3))


def run_refine(
    client: Any,
    *,
    model: str,
    system: str,
    user_task: str,
    draft: str,
    critique: str,
) -> str:
    user = (
        f"用户任务：{user_task}\n\n"
        f"初稿：\n{draft}\n\n"
        f"批评意见：\n{critique}\n\n"
        "请根据批评修订，输出须含且仅含 ## 推理 与 ## 结论 两段。"
    )
    resp = create_chat_completion(
        client,
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return resp.choices[0].message.content or ""
