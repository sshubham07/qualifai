"""Shared helpers for hook scripts."""

import json
import sys
from typing import Any


def read_input() -> dict[str, Any]:
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError:
        return {}


def block(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(2)


def edited_path(data: dict[str, Any]) -> str:
    return str((data.get("tool_input") or {}).get("file_path", ""))
