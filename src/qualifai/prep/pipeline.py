"""Prep pipeline orchestration (runs in the worker). Plain async code — no LangGraph needed:
it is a DAG with no cycles and no human input (ADR-0003)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from qualifai.content.loader import round_template, tier_preset
from qualifai.domain.models import InterviewPlan, InterviewRequest
from qualifai.llm.gateway import LLM
from qualifai.prep.extraction import extract_jd, extract_resume
from qualifai.prep.gap_matrix import build_gap_matrix
from qualifai.prep.planner import PlanningConfig, build_plan
from qualifai.prep.topic_packs import build_all_packs

Progress = Callable[[str], Awaitable[None]]


async def prepare_kit(llm: LLM, req: InterviewRequest, progress: Progress) -> InterviewPlan:
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
    return plan.model_copy(update={"topics": tuple(topics)})
