"""Intake gate — the first step of the prep job, before any large-model work (ADR-0016).

A small local model classifies both documents (is-resume, is-JD, role family of each); code
decides whether prep goes on. Both the resume and the JD must be for a software role.
"""

from __future__ import annotations

from qualifai.content.loader import role_family
from qualifai.domain.enums import FailureCode, RoleFamily, SupportLevel
from qualifai.domain.models import IntakeResult, InterviewRequest
from qualifai.llm.gateway import LLM
from qualifai.llm.prompts import load_prompt
from qualifai.llm.tasks import LLMTask

MIN_CONFIDENCE = 0.6
INJECTION_MARKERS = (
    "ignore previous",
    "ignore all previous",
    "system prompt",
    "rate this candidate",
)


def heuristic_injection(text: str) -> bool:
    low = text.lower()
    return any(m in low for m in INJECTION_MARKERS)


def _support(family: RoleFamily) -> SupportLevel:
    """Which roles count as software engineering is content (content/role_families/*.yaml)."""
    spec = role_family(family)
    return spec.support if spec else SupportLevel.UNSUPPORTED


def decide(result: IntakeResult) -> SupportLevel | FailureCode:
    """Deterministic decision from the classification: a support level, or why prep stops."""
    if not result.is_resume:
        return FailureCode.NOT_A_RESUME
    if not result.is_jd:
        return FailureCode.NOT_A_JD
    if RoleFamily.UNKNOWN in (result.resume_role_family, result.jd_role_family):
        return FailureCode.UNDECIDED
    # A non-software family is rejected whatever the confidence: small models report low
    # confidence for a mismatched pair, and the specific reason is more useful than "undecided".
    if _support(result.jd_role_family) is SupportLevel.UNSUPPORTED:
        return FailureCode.JD_NOT_SOFTWARE
    if _support(result.resume_role_family) is SupportLevel.UNSUPPORTED:
        return FailureCode.RESUME_NOT_SOFTWARE
    if result.confidence < MIN_CONFIDENCE:
        return FailureCode.UNDECIDED
    return _support(result.jd_role_family)


async def run_intake(llm: LLM, req: InterviewRequest) -> IntakeResult:
    result = await llm.structured(
        LLMTask.INTAKE_GATE,
        system=load_prompt("intake_gate"),
        user=(
            f"<doc type='jd'>{req.jd_text[:4000]}</doc>\n"
            f"<doc type='resume'>{req.resume_text[:3000]}</doc>"
        ),
        schema=IntakeResult,
    )
    if heuristic_injection(req.resume_text):
        result = result.model_copy(update={"injection_suspected": True})
    return result
