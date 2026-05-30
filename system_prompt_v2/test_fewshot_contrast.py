# -*- coding: utf-8 -*-
"""非交互：对比 Few-shot / Zero-shot 对同一短 prompt 的输出形态。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_PKG = Path(__file__).resolve().parent
load_dotenv(_PKG / ".env", override=False)
load_dotenv(_PKG.parent / "minimal_chat_v1" / ".env", override=False)

from prompt_session import PromptAgentSession  # noqa: E402

PROMPT = "请判断下面句子的情绪，句子：需求评审被驳回了。"


def is_clean_json_line(reply: str) -> bool:
    s = reply.strip()
    if not s or "\n" in s or "```" in s:
        return False
    return s.startswith("{") and s.endswith("}") and "label" in s


def is_prose_or_markdown(reply: str) -> bool:
    if "```" in reply:
        return True
    s = reply.strip()
    if "\n" in s:
        return True
    if is_clean_json_line(s):
        return False
    return any(w in s for w in ("如下", "结果", "分类", "情绪是", "倾向于"))


def run_once(include_few_shot: bool) -> tuple[str, int]:
    session = PromptAgentSession(include_few_shot=include_few_shot)
    seed = len(session.messages)
    reply, _snap = session.chat(PROMPT)
    return reply.strip(), seed


def main() -> int:
    key = os.getenv("ZHIPU_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not key or key.strip() in {"你的Key", "你的智谱Key", "你的智谱APIKey"}:
        print("未检测到有效 ZHIPU_API_KEY。")
        print("请用真实 Key（不是占位符「你的智谱Key」），在同一终端执行：")
        print('  $env:ZHIPU_API_KEY="sk-xxxxxxxx"')
        print("  python test_fewshot_contrast.py")
        print("或复制 .env.example 为 .env，填入 Key 后重试。")
        return 1

    print("测试句:", PROMPT)
    print("-" * 60)

    results: dict[str, str] = {}
    for label, few in [("Few-shot", True), ("Zero-shot", False)]:
        try:
            reply, seed = run_once(few)
        except Exception as e:
            print(f"[{label}] 调用失败: {e}")
            return 1
        results[label] = reply
        kind = "单行 JSON" if is_clean_json_line(reply) else (
            "Markdown/多行" if is_prose_or_markdown(reply) else "其他"
        )
        print(f"\n=== {label}（种子 {seed} 条）===")
        print(f"形态: {kind}")
        print("输出:")
        print(reply)
        print("-" * 60)

    few_ok = is_clean_json_line(results["Few-shot"])
    zero_ok = is_prose_or_markdown(results["Zero-shot"]) and not is_clean_json_line(
        results["Zero-shot"]
    )
    print()
    if few_ok and zero_ok:
        print("对照达标：Few-shot 为单行 JSON，Zero-shot 为说明句或 Markdown。")
        return 0
    print("对照未达标：")
    if not few_ok:
        print("  - Few-shot 未得到单行 JSON，请检查 few_shot.json / system 后缀。")
    if not zero_ok:
        print("  - Zero-shot 仍过于接近 JSON，请确认 USE_FEW_SHOT=0 且 system 无结构化后缀。")
    return 2


if __name__ == "__main__":
    sys.exit(main())
