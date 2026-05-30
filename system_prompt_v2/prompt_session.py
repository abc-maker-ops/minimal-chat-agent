# -*- coding: utf-8 -*-
"""
system_prompt_v2：第 03 课。在 minimal_chat_v1 上增加 system 与可选 Few-shot 范例。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_LAB / "minimal_chat_v1"))

from agent_session import AgentSession  # noqa: E402

PROMPT_DIR = Path(__file__).resolve().parent / "prompts"

_FEW_SHOT_SYSTEM_SUFFIX = (
    "情绪分类等结构化任务：严格模仿 Few-shot 范例，"
    "只输出一行 JSON，不要前后说明，不要用 Markdown 代码块包裹。"
)


def load_system_prompt(*, include_few_shot: bool = True) -> str:
    text = (PROMPT_DIR / "system.txt").read_text(encoding="utf-8").strip()
    if include_few_shot:
        text = f"{text}\n\n{_FEW_SHOT_SYSTEM_SUFFIX}"
    return text


def load_few_shot_messages() -> list[dict]:
    path = PROMPT_DIR / "few_shot.json"
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    messages: list[dict] = []
    for item in raw:
        messages.append({"role": "user", "content": item["user"]})
        messages.append({"role": "assistant", "content": item["assistant"]})
    return messages


def build_seed_messages(include_few_shot: bool = True) -> list[dict]:
    messages: list[dict] = [
        {"role": "system", "content": load_system_prompt(include_few_shot=include_few_shot)}
    ]
    if include_few_shot:
        messages.extend(load_few_shot_messages())
    return messages


class PromptAgentSession(AgentSession):
    """在 v1 会话上固定 system，并可选注入 Few-shot 范例。"""

    def __init__(self, include_few_shot: bool = True) -> None:
        super().__init__()
        self.include_few_shot = include_few_shot
        self.messages = build_seed_messages(include_few_shot)

    def reset(self):
        super().reset()
        self.messages = build_seed_messages(self.include_few_shot)
        return self.snapshot()
