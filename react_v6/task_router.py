# -*- coding: utf-8 -*-
"""按任务描述自动决定是否走计划比选、批评精炼（用户不选模式）。"""
from __future__ import annotations

from dataclasses import dataclass

_DELIVERABLE = ("汇总", "写文件", "生成", "报告", "交付", "整理", "输出", "写入", "导出")
_MULTI_STEP = ("多个", "多份", "分别", "步骤", "第一", "然后", "接着", "之后")
_FORMAT_HEAVY = ("格式", "规范", "条目", "表格", "markdown", "Markdown", "## 结论")


@dataclass(frozen=True)
class TaskRoute:
    use_tot: bool
    use_refine: bool
    tot_reason: str
    refine_reason: str


def analyze_task(user_text: str) -> TaskRoute:
    text = user_text.strip()
    use_tot = False
    use_refine = False
    tot_reason = ""
    refine_reason = ""

    if any(k in text for k in _DELIVERABLE):
        use_tot = True
        tot_reason = "任务含交付/汇总类表述"
        use_refine = True
        refine_reason = "交付类输出，自动做一轮修订"
    elif len(text) > 72 or text.count("，") >= 3 or any(k in text for k in _MULTI_STEP):
        use_tot = True
        tot_reason = "多步或较长任务描述"

    if not use_refine and any(k in text for k in _FORMAT_HEAVY):
        use_refine = True
        refine_reason = "输出格式要求较高"

    return TaskRoute(
        use_tot=use_tot,
        use_refine=use_refine,
        tot_reason=tot_reason,
        refine_reason=refine_reason,
    )
