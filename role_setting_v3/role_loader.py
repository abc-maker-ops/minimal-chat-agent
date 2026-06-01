# -*- coding: utf-8 -*-
"""加载并校验 prompts/roles/*.yaml。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

PROMPT_DIR = Path(__file__).resolve().parent / "prompts"
ROLES_DIR = PROMPT_DIR / "roles"


@dataclass(frozen=True)
class RoleSpec:
    id: str
    display_name: str
    version: str
    system_body: str
    rules: tuple[str, ...]
    few_shot_ref: str | None
    routing_hint: str
    keywords: tuple[str, ...]

    def compose_system(self, *, include_few_shot: bool = True) -> str:
        parts = [self.system_body.strip()]
        if self.rules:
            parts.append("")
            parts.append("规则：")
            for i, rule in enumerate(self.rules, start=1):
                parts.append(f"{i}. {rule.strip()}")
        if include_few_shot and self.few_shot_ref:
            parts.append("")
            parts.append(
                "情绪分类等结构化任务：严格模仿 Few-shot 范例，"
                "只输出一行 JSON，不要前后说明，不要用 Markdown 代码块包裹。"
            )
        return "\n".join(parts).strip()


def _parse_role(data: dict, path: Path) -> RoleSpec:
    for key in ("id", "display_name", "version", "system_body"):
        if key not in data or not str(data[key]).strip():
            raise ValueError(f"角色文件缺少必填字段 {key!r}: {path}")
    rules_raw = data.get("rules") or []
    if not isinstance(rules_raw, list):
        raise ValueError(f"rules 必须是列表: {path}")
    keywords_raw = data.get("keywords") or []
    if not isinstance(keywords_raw, list):
        raise ValueError(f"keywords 必须是列表: {path}")
    few_shot_ref = data.get("few_shot_ref")
    if few_shot_ref is not None:
        few_shot_ref = str(few_shot_ref).strip() or None
    return RoleSpec(
        id=str(data["id"]).strip(),
        display_name=str(data["display_name"]).strip(),
        version=str(data["version"]).strip(),
        system_body=str(data["system_body"]).strip(),
        rules=tuple(str(r).strip() for r in rules_raw if str(r).strip()),
        few_shot_ref=few_shot_ref,
        routing_hint=str(data.get("routing_hint") or "").strip(),
        keywords=tuple(str(k).strip().lower() for k in keywords_raw if str(k).strip()),
    )


def list_role_ids() -> list[str]:
    if not ROLES_DIR.is_dir():
        return []
    return sorted(p.stem for p in ROLES_DIR.glob("*.yaml"))


def load_role(role_id: str) -> RoleSpec:
    role_id = role_id.strip()
    path = ROLES_DIR / f"{role_id}.yaml"
    if not path.exists():
        known = ", ".join(list_role_ids()) or "（无）"
        raise FileNotFoundError(f"未知角色: {role_id}，缺少 {path}；已知: {known}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"角色文件必须是 YAML 对象: {path}")
    role = _parse_role(data, path)
    if role.id != role_id:
        raise ValueError(f"文件名 {role_id} 与 id 字段 {role.id!r} 不一致: {path}")
    if role.few_shot_ref:
        ref = PROMPT_DIR / role.few_shot_ref
        if not ref.exists():
            raise FileNotFoundError(f"角色 {role_id} 引用的 few_shot 不存在: {ref}")
    return role


def load_all_roles() -> list[RoleSpec]:
    return [load_role(rid) for rid in list_role_ids()]
