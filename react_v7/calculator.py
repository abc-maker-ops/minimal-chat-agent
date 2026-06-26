# -*- coding: utf-8 -*-
"""安全算式求值：仅允许数字与 + - * / 及括号。"""
from __future__ import annotations

import ast
import operator
from typing import Any

_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
_ALLOWED_UNARY = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError("仅支持数字常数")
        return float(node.value)
    if isinstance(node, ast.BinOp):
        op = _ALLOWED_BINOPS.get(type(node.op))
        if op is None:
            raise ValueError("不支持的二元运算符")
        return op(_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp):
        op = _ALLOWED_UNARY.get(type(node.op))
        if op is None:
            raise ValueError("不支持的一元运算符")
        return op(_eval_node(node.operand))
    raise ValueError("不支持的表达式形式")


def _format_number(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return str(value)


def eval_expression(expression: str) -> tuple[str, bool]:
    """返回 (Observation 文本, 是否成功)。"""
    raw = (expression or "").strip()
    if not raw:
        return "错误：表达式为空", False
    if len(raw) > 200:
        return "错误：表达式过长（上限 200 字符）", False
    try:
        tree = ast.parse(raw, mode="eval")
    except SyntaxError as exc:
        return f"错误：语法不合法（{exc.msg}）", False
    try:
        value = _eval_node(tree)
    except ZeroDivisionError:
        return "错误：除数为零", False
    except ValueError as exc:
        return f"错误：{exc}", False
    except Exception:
        return "错误：无法计算该表达式", False
    return _format_number(value), True
