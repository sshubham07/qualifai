"""Prep pipeline orchestration (runs in the worker). Plain async code — no LangGraph needed:
it is a DAG with no cycles and no human input (ADR-0003)."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from qualifai.content.loader import round_template, skill_aliases, tier_preset
from qualifai.domain.enums import FailureCode
from qualifai.domain.errors import PrepRejected
from qualifai.domain.models import (
    Frozen,
    GapRow,
    InterviewPlan,
    InterviewRequest,
    JDSkill,
    MatchReport,
    ResumeClaim,
)
from qualifai.llm.gateway import LLM
from qualifai.prep.extraction import extract_jd, extract_resume
from qualifai.prep.gap_matrix import (
    build_gap_matrix,
    round_skills,
    with_fundamentals,
    with_round_extras,
)
from qualifai.prep.match import assess_match, decide_match, match_reason
from qualifai.prep.opening import write_opening_question
from qualifai.prep.planner import PlanningConfig, build_plan
from qualifai.prep.topic_packs import build_all_packs

Progress = Callable[[str], Awaitable[None]]


class PreparedKit(Frozen):
    """Everything prep produces: the profile (claims, JD skills, gap matrix, match, opening
    question) and the plan."""

    claims: tuple[ResumeClaim, ...]
    jd_skills: tuple[JDSkill, ...]
    gaps: tuple[GapRow, ...]
    match: MatchReport
    resume_years: float | None
    opening_question: str
    plan: InterviewPlan


async def prepare_kit(llm: LLM, req: InterviewRequest, progress: Progress) -> PreparedKit:
    """Raises PrepRejected when there is no fair interview to build from these two documents."""
    template, tier = round_template(req.round_type), tier_preset(req.company_tier)

    await progress("Parsing resume")
    resume = await extract_resume(llm, req.resume_text)
    await progress("Analysing job description")
    jd = await extract_jd(llm, req.jd_text)

    await progress("Finding what to verify and what to test")
    gaps = build_gap_matrix(jd.skills, resume.claims)
    # A focused round (DSA, LLD, HLD, managerial) brings its own topics; the JD still has to fit.
    asked = build_gap_matrix(round_skills(template.skills), resume.claims) or (
        build_gap_matrix(with_round_extras(jd.skills, template.always), resume.claims)
        if gaps
        else []
    )
    if not asked:
        raise PrepRejected(FailureCode.NO_KNOWN_SKILLS)
    asked = with_fundamentals(asked)  # not only project talk (ADR-0023)
    # Stop here, before the expensive question writing, if the resume and the JD are totally off.
    every_jd_skill = build_gap_matrix([*jd.skills, *jd.other_skills], resume.claims)
    match = assess_match(every_jd_skill, req.resume_text, skill_aliases())
    mismatch = decide_match(match)
    if mismatch is not None:
        raise PrepRejected(mismatch, match_reason(match))

    await progress("Building a time-budgeted plan")
    plan = build_plan(
        asked,
        template,
        tier,
        req.target_minutes,
        topic_phase="core",
        cfg=PlanningConfig(experience_max_years=req.experience_max_years),
    )

    await progress("Writing questions and rubrics")
    claims = {c.id: c.text for c in resume.claims}
    topics, opening = await asyncio.gather(
        build_all_packs(llm, list(plan.topics), template, tier, claims),
        write_opening_question(
            llm, req, template, tier, resume.claims, plan.topics, resume.years_experience
        ),
    )
    return PreparedKit(
        claims=tuple(resume.claims),
        jd_skills=tuple(jd.skills),
        gaps=tuple(gaps),
        match=match,
        resume_years=resume.years_experience,
        opening_question=opening,
        plan=plan.model_copy(update={"topics": tuple(topics)}),
    )
