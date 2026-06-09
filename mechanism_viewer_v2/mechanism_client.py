# -*- coding: utf-8 -*-
"""机制查看器 v2：累积观测 agent v1 + v2（Few-shot / Zero-shot）。"""
from __future__ import annotations

import sys
from pathlib import Path

_V1_DIR = Path(__file__).resolve().parent.parent / "mechanism_viewer_v1"
sys.path.insert(0, str(_V1_DIR))

import mechanism_client as _viewer  # noqa: E402

if __name__ == "__main__":
    _viewer.main(default_version="v2_fewshot", profile="viewer2")
