# -*- coding: utf-8 -*-
"""read_file / list_dir / write_text 实现。

三个函数均返回 (Observation 文本, 内部是否成功)；run_tool 只把文本字符串写回 messages。
失败时文本以「错误：」开头，与 v6 calculator 约定一致，便于模型读 Observation 后改参重试。
"""
from __future__ import annotations

from pathlib import Path

from workspace import MAX_READ_BYTES, MAX_WRITE_BYTES, resolve_read_path, resolve_write_path


def read_file(rel_path: str) -> tuple[str, bool]:
    """读取 UTF-8 文本；超过 MAX_READ_BYTES 则拒绝，避免 Observation 撑爆上下文。"""
    target, err = resolve_read_path(rel_path)
    if err or target is None:
        return err or "错误：路径无效", False
    if not target.is_file():
        return f"错误：文件不存在 {rel_path!r}", False
    size = target.stat().st_size
    if size > MAX_READ_BYTES:
        return f"错误：文件过大（{size} 字节，上限 {MAX_READ_BYTES}）", False
    try:
        text = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return "错误：文件须为 UTF-8 文本", False
    except OSError as exc:
        return f"错误：读取失败（{exc}）", False
    return text, True


def list_dir(rel_path: str = "") -> tuple[str, bool]:
    """列目录；空字符串表示工作区根。子目录名以 / 结尾，便于模型区分文件与文件夹。"""
    target, err = resolve_read_path(rel_path)
    if err or target is None:
        return err or "错误：路径无效", False
    if not target.is_dir():
        return f"错误：目录不存在 {rel_path!r}", False
    try:
        names = sorted(p.name + ("/" if p.is_dir() else "") for p in target.iterdir())
    except OSError as exc:
        return f"错误：列目录失败（{exc}）", False
    if not names:
        return "（空目录）", True
    return "\n".join(names), True


def write_text(rel_path: str, content: str) -> tuple[str, bool]:
    """写入 output/ 下路径；自动创建父目录。成功时 Observation 为「已写入 …（N 字节）」。"""
    target, err = resolve_write_path(rel_path)
    if err or target is None:
        return err or "错误：路径无效", False
    body = content if content is not None else ""
    encoded = body.encode("utf-8")
    if len(encoded) > MAX_WRITE_BYTES:
        return f"错误：内容过大（{len(encoded)} 字节，上限 {MAX_WRITE_BYTES}）", False
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8", newline="\n")
    except OSError as exc:
        return f"错误：写入失败（{exc}）", False
    return f"已写入 {rel_path}（{len(encoded)} 字节）", True
