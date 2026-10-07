"""PostToolUse: fast architecture feedback — deterministic modules must stay pure (ADR-0002).
import-linter enforces the same rule in CI; this hook catches it the moment the file is written."""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _common import block, edited_path, read_input

PURE_MODULES = (
    "src/qualifai/interview/policy.py",
    "src/qualifai/interview/time_window.py",
    "src/qualifai/interview/coverage.py",
    "src/qualifai/eval/aggregation.py",
    "src/qualifai/eval/verdict.py",
    "src/qualifai/eval/evidence_check.py",
)
FORBIDDEN = re.compile(
    r"^\s*(from|import)\s+(qualifai\.llm|qualifai\.db|langgraph|openai|sqlalchemy)\b", re.M
)

path = edited_path(read_input())
if path.endswith(PURE_MODULES) and os.path.exists(path):
    with open(path) as fh:
        hit = FORBIDDEN.search(fh.read())
    if hit:
        block(
            f"Architecture violation in {path}: '{hit.group(0).strip()}'.\n"
            "This module is part of the deterministic core (policy/time/scoring). Pass the data in "
            "as arguments instead of importing LLM/DB code. See ADR-0002."
        )

if path.endswith(".py") and "/src/qualifai/" in path and "qualifai/llm/" not in path:
    with open(path) as fh:
        if re.search(r"^\s*(from|import)\s+openai\b", fh.read(), re.M):
            block(f"{path}: only qualifai.llm may import provider SDKs (ADR-0004). Use LLMGateway.")
sys.exit(0)
