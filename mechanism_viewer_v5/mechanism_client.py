# -*- coding: utf-8 -*-
"""机制查看器 v5：reflection_v5 质检与修订。"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent / "mechanism_viewer_v1"
_spec = importlib.util.spec_from_file_location("mechanism_viewer_core", _root / "mechanism_client.py")
if _spec is None or _spec.loader is None:
    raise ImportError("无法加载 mechanism_viewer_v1/mechanism_client.py")
_viewer = importlib.util.module_from_spec(_spec)
sys.modules["mechanism_viewer_core"] = _viewer
_spec.loader.exec_module(_viewer)

if __name__ == "__main__":
    _viewer.main(default_version="v5_refine_fewshot", profile="viewer5")
