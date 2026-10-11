"""Resume / JD extraction with the large model → structured, normalised domain objects."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from pydantic import BaseModel

from qualifai.content.loader import skill_aliases, skill_parents
from qualifai.domain.models import JDSkill, ResumeClaim
from qualifai.llm.gateway import LLM
from qualifai.llm.prompts import load_prompt
from qualifai.llm.tasks import LLMTask
from qualifai.prep.taxonomy import normalize_skill


class ResumeExtraction(BaseModel):
    claims: list[ResumeClaim]
    years_experience: float | None = None


class JDExtraction(BaseModel):
    skills: list[JDSkill]  # after normalisation: taxonomy skills only — what we can ask about
    seniority_signals: list[str] = []
    responsibilities: list[str] = []
    # Set by code, never by the model: skills outside the taxonomy, kept for the match check.
    other_skills: list[JDSkill] = []


def _claim_skills(
    raw: Iterable[str], aliases: Mapping[str, str], parents: Mapping[str, str]
) -> tuple[str, ...]:
    """Canonical ids plus their parents (FastAPI shows Python); unknown skills stay as typed."""
    out: dict[str, None] = {}  # ordered set
    for name in raw:
        skill = normalize_skill(name, aliases)
        if skill is None:
            out[name.strip().lower()] = None
        while skill is not None and skill not in out:
            out[skill] = None
            skill = parents.get(skill)
    return tuple(s for s in out if s)


async def extract_resume(llm: LLM, resume_text: str) -> ResumeExtraction:
    out = await llm.structured(
        LLMTask.RESUME_EXTRACT,
        system=load_prompt("resume_extract"),
        user=f"<resume>{resume_text}</resume>",
        schema=ResumeExtraction,
    )
    aliases, parents = skill_aliases(), skill_parents()
    claims = [
        c.model_copy(update={"skills": _claim_skills(c.skills, aliases, parents)})
        for c in out.claims
    ]
    return out.model_copy(update={"claims": claims})


def _keep_heaviest(merged: dict[str, JDSkill], name: str, skill: JDSkill) -> None:
    prev = merged.get(name)
    if prev is None or skill.weight > prev.weight:
        merged[name] = skill.model_copy(update={"name": name})


async def extract_jd(llm: LLM, jd_text: str) -> JDExtraction:
    out = await llm.structured(
        LLMTask.JD_EXTRACT,
        system=load_prompt("jd_extract"),
        user=f"<jd>{jd_text}</jd>",
        schema=JDExtraction,
    )
    aliases = skill_aliases()
    known: dict[str, JDSkill] = {}
    other: dict[str, JDSkill] = {}
    for s in out.skills:
        canonical = normalize_skill(s.name, aliases)
        if canonical is not None:
            _keep_heaviest(known, canonical, s)
        elif s.name.strip():  # TODO(spec-001 T-14): log unknown skill for the demand report
            _keep_heaviest(other, s.name.strip().lower(), s)
    return out.model_copy(
        update={"skills": list(known.values()), "other_skills": list(other.values())}
    )
