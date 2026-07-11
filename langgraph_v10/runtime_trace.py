# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass, field

from bridge_v8 import TaskRoute


@dataclass
class RuntimeTrace:
    """LangGraph 运行轨迹（供机制查看器 v10）。"""

    route: TaskRoute
    role_id: str = ""
    role_source: str = ""
    route_reason: str = ""
    tot_used: bool = False
    selected_plan: str = ""
    plan_select_reason: str = ""
    graph_steps: int = 0
    graph_hit_limit: bool = False
    tool_count: int = 0
    refine_used: bool = False
    done_ok: bool | None = None
    node_path_summary: str = ""
    policy_summary: str = ""
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
            "② 编排：LangGraph StateGraph（agent ↔ tools 环 + force_done_gate）"
        )
        if self.node_path_summary:
            lines.append(f"   节点路径：{self.node_path_summary}")
        if self.policy_summary:
            lines.append(f"   工具策略：{self.policy_summary}")

        if self.tot_used:
            reason = self.route.tot_reason or "内部触发"
            lines.append(f"③ 计划比选：已执行（{reason}）")
        else:
            lines.append("③ 计划比选：跳过（简单任务）")

        limit_note = " · 已达步数上限" if self.graph_hit_limit else ""
        lines.append(
            f"④ LangGraph：{self.graph_steps} 次 agent 节点，工具 {self.tool_count} 次{limit_note}"
        )

        if self.done_ok is True:
            lines.append("⑤ done 验收：通过（结构化交付已校验）")
        elif self.done_ok is False:
            lines.append("⑤ done 验收：未通过（见工具链 Observation）")
        else:
            lines.append("⑤ done 验收：本轮未调用")

        if self.refine_used:
            lines.append("⑥ 批评与精炼：已执行一轮")
        else:
            lines.append("⑥ 批评与精炼：跳过")

        self.lines = lines
        return lines

    def as_text(self) -> str:
        if not self.lines:
            self.build_lines()
        return "\n".join(self.lines)
