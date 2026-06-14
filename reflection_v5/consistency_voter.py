# -*- coding: utf-8 -*-
"""自洽性（Self-Consistency）：同一任务多次采样，对结论段投票。"""
from __future__ import annotations

import os
from collections import Counter
from dataclasses import dataclass

from cot_parser import CotSections


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


def resolve_consistency_threshold() -> float:
    raw = (os.getenv("CONSISTENCY_THRESHOLD") or "0.67").strip()
    try:
        return float(raw)
    except ValueError:
        return 0.67


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
