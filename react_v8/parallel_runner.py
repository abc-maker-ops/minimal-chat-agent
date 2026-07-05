# -*- coding: utf-8 -*-
"""Parallel Function Calling：客户端并行执行 tool_calls。"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

PARALLEL_SAFE_TOOLS = frozenset({"read_file", "list_dir", "calculator"})


def can_run_parallel(tool_names: list[str]) -> bool:
    if len(tool_names) <= 1:
        return False
    return all(name in PARALLEL_SAFE_TOOLS for name in tool_names)


def execute_tool_calls(
    tool_calls: list[Any],
    run_tool: Callable[[str, str], str],
    observation_ok: Callable[[str, str], bool],
    *,
    parallel: bool,
    react_round: int,
    start_step: int,
) -> list[tuple[Any, str, bool, int, int | None]]:
    """执行一批 tool_calls，返回 (tc, observation, ok, step_no, parallel_group)。"""
    names = [tc.function.name for tc in tool_calls]
    use_parallel = parallel and can_run_parallel(names)
    group_id = react_round + 1 if use_parallel else None

    def _one(tc: Any) -> tuple[Any, str, bool]:
        fn = tc.function
        args = fn.arguments or "{}"
        obs = run_tool(fn.name, args)
        ok = observation_ok(obs, fn.name)
        return tc, obs, ok

    results: list[tuple[Any, str, bool]]
    if use_parallel:
        with ThreadPoolExecutor(max_workers=min(4, len(tool_calls))) as pool:
            results = list(pool.map(_one, tool_calls))
    else:
        results = [_one(tc) for tc in tool_calls]

    out: list[tuple[Any, str, bool, int, int | None]] = []
    for idx, (tc, obs, ok) in enumerate(results):
        out.append((tc, obs, ok, start_step + idx, group_id))
    return out
