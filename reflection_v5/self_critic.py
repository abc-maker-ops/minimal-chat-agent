# -*- coding: utf-8 -*-
"""自我批评：对已有一份成稿列举问题，不直接输出修订稿。"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "minimal_chat_v1"))
from api_resilience import create_chat_completion  # noqa: E402


def run_self_critic(
    client: Any,
    *,
    model: str,
    system: str,
    user_task: str,
    draft: str,
) -> str:
    user = (
        f"用户任务：{user_task}\n\n"
        f"待批评的助手回复：\n{draft}\n\n"
        "请列出该回复的问题（漏项、逻辑、格式、与角色冲突等），"
        "用条目列表输出，不要给出修订稿。"
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
