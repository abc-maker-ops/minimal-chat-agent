# -*- coding: utf-8 -*-
"""done 工具：按 Markdown / JSON / XML 规则机器验收交付物。

与 write_text 解耦：先按路径读盘，再按 format 分支校验。
所有结果收成同一 JSON 形状 {"ok", "message", ...}，供 _observation_ok 与机制查看器解析。
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from workspace import resolve_read_path


def _result(ok: bool, message: str, **extra: Any) -> tuple[str, bool]:
    """统一 Observation 格式：JSON 字符串 + 布尔 ok（供 run_tool 与轨迹 FAIL 标记）。"""
    payload: dict[str, Any] = {"ok": ok, "message": message}
    payload.update(extra)
    return json.dumps(payload, ensure_ascii=False), ok


def validate_delivery(
    rel_path: str,
    fmt: str,
    rules: dict[str, Any] | None = None,
) -> tuple[str, bool]:
    """done 工具入口：读交付文件 → 按 format 调用 _validate_*。"""
    rules = rules or {}
    target, err = resolve_read_path(rel_path)
    if err or target is None:
        return _result(False, err or "路径无效")
    if not target.is_file():
        return _result(False, f"交付文件不存在：{rel_path!r}")

    fmt_norm = (fmt or "").strip().lower()
    try:
        text = target.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as exc:
        return _result(False, f"无法读取交付文件：{exc}")

    if fmt_norm == "markdown":
        return _validate_markdown(text, rules)
    if fmt_norm == "json":
        return _validate_json(text, rules)
    if fmt_norm == "xml":
        return _validate_xml(text, rules)
    return _result(False, f"不支持的 format：{fmt!r}（可用 markdown / json / xml）")


def _markdown_heading_line_present(text: str, heading: str) -> bool:
    """检查是否存在与 heading 匹配的 Markdown 标题行（非正文子串）。

    例如 required_headings 为 ## 结论 时，须有一行形如 ``## 结论`` 的标题；
    正文中仅提到「## 结论」字样不算通过。
    """
    token = heading.strip()
    if not token:
        return True
    matched = re.match(r"^(#+)\s*(.+)$", token)
    if not matched:
        for line in text.splitlines():
            if line.strip() == token:
                return True
        return False
    level = len(matched.group(1))
    title = matched.group(2).strip()
    line_re = re.compile(rf"^#{{{level}}}\s+{re.escape(title)}\s*$")
    return any(line_re.match(line.strip()) for line in text.splitlines())


def _validate_markdown(text: str, rules: dict[str, Any]) -> tuple[str, bool]:
    headings = rules.get("required_headings") or []
    if not isinstance(headings, list):
        headings = []
    missing: list[str] = []
    for h in headings:
        token = str(h).strip()
        if token and not _markdown_heading_line_present(text, token):
            missing.append(token)
    if missing:
        return _result(False, f"缺少必需标题：{', '.join(missing)}", missing=missing)
    return _result(True, "Markdown 验收通过", path_checked=True)


def _validate_json(text: str, rules: dict[str, Any]) -> tuple[str, bool]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return _result(False, f"JSON 解析失败：{exc.msg}")
    if not isinstance(data, dict):
        return _result(False, "JSON 根节点须为对象")
    keys = rules.get("required_keys") or []
    if not isinstance(keys, list):
        keys = []
    missing = [str(k) for k in keys if str(k) not in data]
    if missing:
        return _result(False, f"缺少必需字段：{', '.join(missing)}", missing=missing)
    return _result(True, "JSON 验收通过", keys_present=list(data.keys()))


def _validate_xml(text: str, rules: dict[str, Any]) -> tuple[str, bool]:
    root_tag = str(rules.get("root_tag") or rules.get("root_element") or "").strip()
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        return _result(False, f"XML 解析失败：{exc}")
    if root_tag and root.tag != root_tag:
        return _result(
            False,
            f"根元素应为 {root_tag!r}，实际为 {root.tag!r}",
        )
    return _result(True, "XML 验收通过", root=root.tag)
