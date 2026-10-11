"""Opening question — the first thing the candidate is asked, written during prep from their
strongest claims and the JD's priorities so the interview can start without a model call."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import Field

from qualifai.content.loader import RoundTemplate, TierPreset
from qualifai.domain.enums import TopicPriority
from qualifai.domain.models import Frozen, InterviewRequest, PlannedTopic, ResumeClaim
from qualifai.llm.gateway import LLM
from qualifai.llm.prompts import load_prompt
from qualifai.llm.tasks import LLMTask

MAX_CLAIMS = 3


class OpeningQuestion(Frozen):
    question: str = Field(min_length=20, max_length=600)


def _lead_claims(claims: Sequence[ResumeClaim], topics: Sequence[PlannedTopic]) -> list[str]:
    """Claims the plan is going to verify come first: the opening leads into them."""
    planned = {t.claim_id for t in topics if t.claim_id}
    ordered = sorted(claims, key=lambda c: c.id not in planned)  # stable: resume order within each
    return [c.text for c in ordered[:MAX_CLAIMS]]


async def write_opening_question(
    llm: LLM,
    req: InterviewRequest,
    template: RoundTemplate,
    tier: TierPreset,
    claims: Sequence[ResumeClaim],
    topics: Sequence[PlannedTopic],
    resume_years: float | None,
) -> str:
    focus = [s for t in topics if t.priority is TopicPriority.MUST for s in t.skills]
    prompt = load_prompt("opening_question").format(
        round_name=template.name,
        tier_name=tier.name,
        tier_guidance=tier.guidance,
        experience_range=f"{req.experience_min_years}–{req.experience_max_years}",
        resume_years=resume_years if resume_years is not None else "not stated",
        claims="\n".join(f"- {c}" for c in _lead_claims(claims, topics)) or "none",
        focus_skills=", ".join(focus) or "general",
    )
    out = await llm.structured(LLMTask.OPENING_QUESTION, "JSON only.", prompt, OpeningQuestion)
    return out.question.strip()
