# -*- coding: utf-8 -*-
"""自洽性（Self-Consistency）：同一任务多次采样，对结论段投票。"""
from __future__ import annotations

import os
from collections import Counter
from dataclasses import dataclass
from typing import Any, Callable

from cot_parser import CotSections, parse_cot


def _normalize(text: str) -> str:
    return " ".join((text or "").split()).strip().lower()


@dataclass(frozen=True)
class ConsistencyResult:
    samples: tuple[CotSections, ...]
    conclusions: tuple[str, ...]
    winner: str
    winner_count: int
    agreement_rate: float
    chosen: CotSections | None


def resolve_consistency_samples() -> int:
    raw = (os.getenv("CONSISTENCY_SAMPLES") or "3").strip()
    try:
        n = int(raw)
    except ValueError:
        n = 3
    return max(2, min(n, 5))


def vote_conclusions(conclusions: list[str]) -> tuple[str, int, float]:
    if not conclusions:
        return "", 0, 0.0
    keys = [_normalize(c) for c in conclusions]
    counter = Counter(keys)
    winner_key, winner_count = counter.most_common(1)[0]
    for orig, key in zip(conclusions, keys):
        if key == winner_key:
            return orig.strip(), winner_count, winner_count / len(conclusions)
    return conclusions[0].strip(), winner_count, winner_count / len(conclusions)


def run_consistency(
    chat_once: Callable[[], tuple[str, CotSections | None]],
    *,
    samples: int | None = None,
) -> ConsistencyResult:
    n = samples if samples is not None else resolve_consistency_samples()
    parsed_list: list[CotSections] = []
    conclusions: list[str] = []
    for _ in range(n):
        _reply, cot = chat_once()
        if cot is None:
            cot = parse_cot(_reply)
        parsed_list.append(cot)
        conclusions.append(cot.conclusion or _reply.strip())
    winner, winner_count, rate = vote_conclusions(conclusions)
    chosen: CotSections | None = None
    for cot in parsed_list:
        if (cot.conclusion or "").strip() == winner or _normalize(cot.conclusion) == _normalize(winner):
            chosen = cot
            break
    if chosen is None and parsed_list:
        chosen = parsed_list[0]
    return ConsistencyResult(
        samples=tuple(parsed_list),
        conclusions=tuple(conclusions),
        winner=winner,
        winner_count=winner_count,
        agreement_rate=rate,
        chosen=chosen,
    )
