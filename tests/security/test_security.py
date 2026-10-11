"""Security checks: intake refusals, prompt-injection handling, and the Claude Code hooks."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from qualifai.domain.enums import FailureCode, RoleFamily
from qualifai.domain.models import IntakeResult
from qualifai.llm.prompts import load_prompt
from qualifai.prep.intake_gate import decide

pytestmark = pytest.mark.security
ROOT = Path(__file__).resolve().parents[2]
HOOKS = ROOT / ".claude" / "hooks"


def intake(**kw) -> IntakeResult:
    base = {
        "jd_role_family": RoleFamily.BACKEND_SDE,
        "confidence": 0.9,
        "resume_role_family": RoleFamily.BACKEND_SDE,
        "is_resume": True,
        "is_jd": True,
    }
    base.update(kw)
    return IntakeResult(**base)


def test_non_technical_role_is_declined():
    assert decide(intake(jd_role_family=RoleFamily.NON_TECHNICAL)) is FailureCode.JD_NOT_SOFTWARE


def test_non_resume_upload_is_rejected():
    assert decide(intake(is_resume=False)) is FailureCode.NOT_A_RESUME


@pytest.mark.parametrize(
    "prompt",
    [
        "intake_gate",
        "resume_extract",
        "jd_extract",
        "opening_question",
        "turn_analyzer",
        "topic_eval",
        "question_gen",
    ],
)
def test_prompts_carry_injection_or_secrecy_rules(prompt):
    text = load_prompt(prompt).lower()
    assert ("never follow instructions" in text) or ("never reveal" in text) or ("quote" in text)


def run_hook(name: str, payload: dict) -> int:
    return subprocess.run(
        [sys.executable, str(HOOKS / name)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
    ).returncode


def test_hook_blocks_env_edits():
    assert run_hook("protect_files.py", {"tool_input": {"file_path": "/repo/.env"}}) == 2
    assert run_hook("protect_files.py", {"tool_input": {"file_path": "/repo/.env.example"}}) == 0


def test_hook_blocks_destructive_bash():
    assert run_hook("guard_bash.py", {"tool_input": {"command": "docker compose down -v"}}) == 2
    assert run_hook("guard_bash.py", {"tool_input": {"command": "make test"}}) == 0


def test_architecture_hook_blocks_llm_import_in_policy(tmp_path):
    fake = tmp_path / "src" / "qualifai" / "interview" / "policy.py"
    fake.parent.mkdir(parents=True)
    fake.write_text("from qualifai.llm.gateway import LLMGateway\n")
    assert run_hook("architecture_guard.py", {"tool_input": {"file_path": str(fake)}}) == 2
