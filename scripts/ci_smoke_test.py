# -*- coding: utf-8 -*-
"""Offline CI smoke test for agent_lab — no LLM API key required."""
from __future__ import annotations

import compileall
import json
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
MODULES = [
    "minimal_chat_v1",
    "system_prompt_v2",
    "role_setting_v3",
    "mechanism_viewer_v1",
    "mechanism_viewer_v2",
]


def check_compile() -> None:
    ok = compileall.compile_dir(str(LAB), quiet=1, workers=0)
    if not ok:
        raise SystemExit("compileall failed for one or more modules")


def check_few_shot_json() -> None:
    path = LAB / "system_prompt_v2" / "prompts" / "few_shot.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or len(raw) < 1:
        raise SystemExit("few_shot.json must be a non-empty list")
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise SystemExit(f"few_shot.json[{i}] must be an object")
        for key in ("user", "assistant"):
            if key not in item or not str(item[key]).strip():
                raise SystemExit(f"few_shot.json[{i}] missing non-empty {key!r}")


def check_prompt_assets() -> None:
    system_txt = LAB / "system_prompt_v2" / "prompts" / "system.txt"
    if not system_txt.read_text(encoding="utf-8").strip():
        raise SystemExit("system.txt is empty")


def check_v3_roles() -> None:
    try:
        import yaml
    except ImportError as e:
        raise SystemExit("PyYAML required for v3 role check: pip install PyYAML") from e
    roles_dir = LAB / "role_setting_v3" / "prompts" / "roles"
    files = sorted(roles_dir.glob("*.yaml"))
    if len(files) < 2:
        raise SystemExit("role_setting_v3 needs at least 2 role yaml files")
    for path in files:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for key in ("id", "display_name", "version", "system_body"):
            if key not in data or not str(data[key]).strip():
                raise SystemExit(f"{path.name} missing {key!r}")


def main() -> int:
    print("agent_lab CI smoke test")
    print("-" * 40)
    for name in MODULES:
        req = LAB / name / "requirements.txt"
        if not req.exists():
            print(f"[skip] {name}: no requirements.txt")
            continue
        print(f"[ok]   {name}/requirements.txt")
    check_prompt_assets()
    print("[ok]   system_prompt_v2/prompts/system.txt")
    check_few_shot_json()
    print("[ok]   system_prompt_v2/prompts/few_shot.json")
    check_v3_roles()
    print("[ok]   role_setting_v3/prompts/roles/*.yaml")
    check_compile()
    print("[ok]   compileall")
    print("-" * 40)
    print("Smoke test passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
