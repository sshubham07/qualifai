"""Prep pipeline orchestration (runs in the worker). Plain async code — no LangGraph needed:
it is a DAG with no cycles and no human input (ADR-0003)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from qualifai.content.loader import round_template, tier_preset
from qualifai.domain.models import (
    Frozen,
    GapRow,
    InterviewPlan,
    InterviewRequest,
    JDSkill,
    ResumeClaim,
)
from qualifai.llm.gateway import LLM
from qualifai.prep.extraction import extract_jd, extract_resume
from qualifai.prep.gap_matrix import build_gap_matrix
from qualifai.prep.planner import PlanningConfig, build_plan
from qualifai.prep.topic_packs import build_all_packs

Progress = Callable[[str], Awaitable[None]]


class PreparedKit(Frozen):
    """Everything prep produces: the profile (claims, JD skills, gap matrix) and the plan."""

    claims: tuple[ResumeClaim, ...]
    jd_skills: tuple[JDSkill, ...]
    gaps: tuple[GapRow, ...]
    plan: InterviewPlan


async def prepare_kit(llm: LLM, req: InterviewRequest, progress: Progress) -> PreparedKit:
    template, tier = round_template(req.round_type), tier_preset(req.company_tier)

    await progress("Parsing resume")
    resume = await extract_resume(llm, req.resume_text)
    await progress("Analysing job description")
    jd = await extract_jd(llm, req.jd_text)

    await progress("Finding what to verify and what to test")
    gaps = build_gap_matrix(jd.skills, resume.claims)

    await progress("Building a time-budgeted plan")
    plan = build_plan(
        gaps,
        template,
        tier,
        req.target_minutes,
        topic_phase="core",
        cfg=PlanningConfig(experience_max_years=req.experience_max_years),
    )

    await progress("Writing questions and rubrics")
    claims = {c.id: c.text for c in resume.claims}
    topics = await build_all_packs(llm, list(plan.topics), template, tier, claims)
    return PreparedKit(
        claims=tuple(resume.claims),
        jd_skills=tuple(jd.skills),
        gaps=tuple(gaps),
        plan=plan.model_copy(update={"topics": tuple(topics)}),
    )
