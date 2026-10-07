#!/usr/bin/env bash
# PostToolUse: format + autofix the edited Python file. Never blocks.
file=$(python3 -c 'import json,sys; print((json.load(sys.stdin).get("tool_input") or {}).get("file_path",""))' 2>/dev/null)
[[ "$file" == *.py && -f "$file" ]] || exit 0
if command -v uv >/dev/null 2>&1; then RUN="uv run"; else RUN=""; fi
$RUN ruff format --quiet "$file" 2>/dev/null || true
$RUN ruff check --fix --quiet "$file" 2>/dev/null || true
exit 0
