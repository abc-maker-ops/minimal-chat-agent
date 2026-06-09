# -*- coding: utf-8 -*-
"""解析 Prompt 层 CoT 输出：## 推理 / ## 结论。"""
from __future__ import annotations

import re
from dataclasses import dataclass

_REASONING = re.compile(r"^##\s*推理\s*$", re.MULTILINE)
_CONCLUSION = re.compile(r"^##\s*结论\s*$", re.MULTILINE)


@dataclass(frozen=True)
class CotSections:
    reasoning: str
    conclusion: str
    ok: bool
    raw: str


def parse_cot(text: str) -> CotSections:
    raw = text or ""
    m_r = _REASONING.search(raw)
    m_c = _CONCLUSION.search(raw)
    if not m_r or not m_c or m_c.start() <= m_r.end():
        return CotSections(reasoning="", conclusion="", ok=False, raw=raw)
    reasoning = raw[m_r.end() : m_c.start()].strip()
    conclusion = raw[m_c.end() :].strip()
    ok = bool(reasoning and conclusion)
    return CotSections(reasoning=reasoning, conclusion=conclusion, ok=ok, raw=raw)
