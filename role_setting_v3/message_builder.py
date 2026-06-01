# -*- coding: utf-8 -*-
"""将 RoleSpec 组装为 messages 固定前缀。"""
from __future__ import annotations

import json
from pathlib import Path

from role_loader import PROMPT_DIR, RoleSpec

PROMPT_DIR = PROMPT_DIR


def load_few_shot_messages(ref: str) -> list[dict]:
    path = PROMPT_DIR / ref
    if not path.exists():
        raise FileNotFoundError(f"Few-shot 文件不存在: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"Few-shot 必须是数组: {path}")
    messages: list[dict] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"Few-shot[{i}] 必须是对象: {path}")
        for key in ("user", "assistant"):
            if key not in item or not str(item[key]).strip():
                raise ValueError(f"Few-shot[{i}] 缺少非空 {key!r}: {path}")
        messages.append({"role": "user", "content": str(item["user"])})
        messages.append({"role": "assistant", "content": str(item["assistant"])})
    return messages


def build_seed_messages(role: RoleSpec, *, include_few_shot: bool = True) -> list[dict]:
    system_content = role.compose_system(include_few_shot=include_few_shot)
    messages: list[dict] = [{"role": "system", "content": system_content}]
    if include_few_shot and role.few_shot_ref:
        messages.extend(load_few_shot_messages(role.few_shot_ref))
    return messages
