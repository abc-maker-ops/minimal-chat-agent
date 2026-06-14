# -*- coding: utf-8 -*-
"""启动机制查看器（viewer5 · reflection_v5）。"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_viewer_spec = importlib.util.spec_from_file_location(
    "mechanism_viewer_v1_client",
    _ROOT / "mechanism_viewer_v1" / "mechanism_client.py",
)
if _viewer_spec is None or _viewer_spec.loader is None:
    raise ImportError("无法加载 mechanism_viewer_v1/mechanism_client.py")
_viewer = importlib.util.module_from_spec(_viewer_spec)
_viewer_spec.loader.exec_module(_viewer)

if __name__ == "__main__":
    _viewer.main(default_version="v5_refine_fewshot", profile="viewer5")
