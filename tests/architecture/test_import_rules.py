"""Architecture fitness tests — same rules as import-linter, runnable without extra tooling."""

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

SRC = Path(__file__).resolve().parents[2] / "src" / "qualifai"
PURE = [
    "interview/policy.py",
    "interview/time_window.py",
    "interview/coverage.py",
    "eval/aggregation.py",
    "eval/verdict.py",
    "eval/evidence_check.py",
]
FORBIDDEN_IN_PURE = ("qualifai.llm", "qualifai.db", "langgraph", "openai", "sqlalchemy")


def imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.add(node.module)
    return out


@pytest.mark.parametrize("rel", PURE)
def test_deterministic_core_is_pure(rel):
    bad = {m for m in imports(SRC / rel) if m.startswith(FORBIDDEN_IN_PURE)}
    assert not bad, f"{rel} imports {bad} — see ADR-0002"


def test_only_llm_package_imports_provider_sdk():
    offenders = [
        p.relative_to(SRC)
        for p in SRC.rglob("*.py")
        if "llm" not in p.relative_to(SRC).parts[:1]
        and any(m == "openai" or m.startswith("openai.") for m in imports(p))
    ]
    assert not offenders, f"Only qualifai.llm may import openai: {offenders}"


def test_domain_has_no_framework_imports():
    for p in (SRC / "domain").rglob("*.py"):
        bad = {
            m
            for m in imports(p)
            if m.startswith(("fastapi", "sqlalchemy", "langgraph", "qualifai.llm"))
        }
        assert not bad, f"{p.name}: {bad}"


def test_api_contains_no_llm_calls():
    for p in (SRC / "api").rglob("*.py"):
        assert not any(m.startswith("qualifai.llm") for m in imports(p)), p.name
