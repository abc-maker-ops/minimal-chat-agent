# -*- coding: utf-8 -*-
"""按用户首句（关键词）自动选角；AGENT_ROLE=auto 时使用。"""
from __future__ import annotations

from role_loader import RoleSpec, load_all_roles


def select_role_id(user_text: str, *, roles: list[RoleSpec] | None = None) -> tuple[str, str]:
    """
    返回 (role_id, reason)。
    教学实现：关键词计分；商用可换 LLM / 向量路由，接口不变。
    """
    catalog = roles if roles is not None else load_all_roles()
    if not catalog:
        raise RuntimeError("角色库为空，无法自动选角")

    text = user_text.strip().lower()
    if not text:
        fallback = catalog[0].id
        return fallback, "空输入，回退默认角色"

    best_id = catalog[0].id
    best_score = -1
    best_reason = "默认首角色"

    for role in catalog:
        score = 0
        hits: list[str] = []
        for kw in role.keywords:
            if kw.lower() in text:
                score += 2
                hits.append(kw)
        if role.routing_hint:
            for token in role.routing_hint.replace("，", " ").replace("、", " ").split():
                token = token.strip().lower()
                if len(token) >= 2 and token in text:
                    score += 1
                    hits.append(token)
        if score > best_score:
            best_score = score
            best_id = role.id
            best_reason = f"关键词匹配: {', '.join(hits)}" if hits else "无命中，暂用该角色"

    if best_score <= 0:
        for role in catalog:
            if role.id == "teacher":
                return role.id, "无关键词命中，回退 teacher"
        return best_id, "无关键词命中，回退默认角色"

    return best_id, best_reason
