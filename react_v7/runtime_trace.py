# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass, field

from task_router import TaskRoute


@dataclass
class RuntimeTrace:
    """本轮 Agent 实际启用的机制（供运行轨迹 Tab）。"""

    route: TaskRoute
    role_id: str = ""
    role_source: str = ""
    route_reason: str = ""
    tot_used: bool = False
    selected_plan: str = ""
    plan_select_reason: str = ""
    react_steps: int = 0
    react_hit_limit: bool = False
    tool_count: int = 0
    refine_used: bool = False
    done_ok: bool | None = None
    lines: list[str] = field(default_factory=list)

    def build_lines(self) -> list[str]:
        lines: list[str] = []
        if self.role_id:
            src = "自动选角" if self.role_source == "auto" else "指定角色"
            extra = f" · {self.route_reason}" if self.route_reason else ""
            lines.append(f"① 角色：{self.role_id}（{src}{extra}）")
        else:
            lines.append("① 角色：待首条消息路由")

        lines.append(
            "② 固定机制：system + Few-shot + Prompt CoT + ReAct "
            "+ read_file / list_dir / write_text / done"
        )

        if self.tot_used:
            reason = self.route.tot_reason or "内部触发"
            lines.append(f"③ 计划比选：已执行（{reason}）")
            if self.selected_plan:
                lines.append(f"   选定计划：{self.selected_plan[:200]}")
            if self.plan_select_reason:
                lines.append(f"   依据：{self.plan_select_reason[:120]}")
        else:
            lines.append("③ 计划比选：跳过（简单任务）")

        lines.append(
            f"④ ReAct：{self.react_steps} 轮 LLM，工具 {self.tool_count} 次"
            + (" · 已达步数上限" if self.react_hit_limit else "")
        )

        if self.done_ok is True:
            lines.append("⑤ done 验收：通过（结构化交付已校验）")
        elif self.done_ok is False:
            lines.append("⑤ done 验收：未通过（见工具链 Observation）")
        else:
            lines.append("⑤ done 验收：本轮未调用")

        if self.refine_used:
            reason = self.route.refine_reason or "内部触发"
            lines.append(f"⑥ 批评与精炼：已执行一轮（{reason}）")
        else:
            lines.append("⑥ 批评与精炼：跳过")

        self.lines = lines
        return lines

    def as_text(self) -> str:
        if not self.lines:
            self.build_lines()
        return "\n".join(self.lines)
