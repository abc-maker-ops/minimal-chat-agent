# -*- coding: utf-8 -*-
"""工作区路径解析（相对路径沙箱，供 read/list/write/done 共用）。

模型通过工具传入的是字符串路径；本模块在程序侧把相对路径解析为磁盘 Path，
并拒绝跳出工作区（如 ..、绝对路径）。读写共用 resolve_read_path，写盘额外要求
路径以 output/ 开头，避免 Agent 误改 input/ 等只读素材。
"""
from __future__ import annotations

import os
from pathlib import Path

MAX_READ_BYTES = 32_768
MAX_WRITE_BYTES = 65_536
OUTPUT_PREFIX = "output/"


def workspace_root() -> Path:
    """工作区根目录；可用环境变量 AGENT_WORKSPACE 覆盖（见正文 3.1 节）。"""
    raw = (os.getenv("AGENT_WORKSPACE") or "").strip()
    if raw:
        return Path(raw).resolve()
    return (Path(__file__).resolve().parent / "workspace").resolve()


def _reject_unsafe_rel(rel: str) -> str | None:
    """拦截不安全相对路径；返回错误文案，或 None 表示通过。"""
    text = (rel or "").strip().replace("\\", "/")
    if not text:
        return "错误：路径为空"
    if text.startswith("/") or (len(text) > 1 and text[1] == ":"):
        return "错误：仅允许工作区相对路径"
    parts = [p for p in text.split("/") if p]
    if any(p in {".", ".."} for p in parts):
        return "错误：路径不得含 .. 或 ."
    return None


def resolve_read_path(rel: str) -> tuple[Path | None, str | None]:
    """读路径：工作区内任意相对路径均可（供 read_file / list_dir / done 读交付物）。"""
    norm = (rel or "").strip().replace("\\", "/")
    root = workspace_root()
    if norm in ("", "."):
        return root, None
    err = _reject_unsafe_rel(norm)
    if err:
        return None, err
    target = (root / norm).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return None, "错误：路径超出工作区"
    return target, None


def resolve_write_path(rel: str) -> tuple[Path | None, str | None]:
    """写路径：除沙箱检查外，还须以 output/ 开头（见 OUTPUT_PREFIX）。"""
    err = _reject_unsafe_rel(rel)
    if err:
        return None, err
    norm = rel.replace("\\", "/")
    if not norm.startswith(OUTPUT_PREFIX):
        return None, f"错误：写入路径须以 {OUTPUT_PREFIX!r} 开头"
    root = workspace_root()
    target = (root / norm).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return None, "错误：路径超出工作区"
    return target, None
