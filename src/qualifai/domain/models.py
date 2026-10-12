"""Core domain models (Pydantic v2). Shared by prep, interview, eval and the API."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from qualifai.domain.enums import (
    AnswerIntent,
    ClaimConsistency,
    ClaimVerdict,
    CompanyTier,
    EvidenceLevel,
    ProbeType,
    RoleFamily,
    RoundType,
    Specificity,
    TopicPriority,
    TopicStatus,
)


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


# ------------------------------------------------------------------ intake
class InterviewRequest(Frozen):
    resume_text: str = Field(min_length=200, max_length=40_000)
    jd_text: str = Field(min_length=100, max_length=20_000)
    round_type: RoundType
    company_tier: CompanyTier
    experience_min_years: int = Field(ge=0, le=40)
    experience_max_years: int = Field(ge=0, le=40)
    target_minutes: int = Field(default=45, ge=15, le=90)
    company_name: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _experience_range_is_ordered(self) -> InterviewRequest:
        if self.experience_min_years > self.experience_max_years:
            raise ValueError("experience_min_years must not exceed experience_max_years")
        return self


class IntakeResult(Frozen):
    """Structured output of the intake gate (LLM). A classification only — code decides."""

    is_resume: bool
    is_jd: bool
    resume_role_family: RoleFamily
    jd_role_family: RoleFamily
    confidence: float = Field(ge=0, le=1)
    injection_suspected: bool = False


# ------------------------------------------------------------------ prep
class ResumeClaim(Frozen):
    id: str
    text: str
    skills: tuple[str, ...]
    ownership_verb: str  # designed / led / built / used / contributed
    metrics: tuple[str, ...] = ()
    evidence_level: EvidenceLevel


class JDSkill(Frozen):
    name: str  # canonical skill id, e.g. "postgresql" (lowercased raw name if not in taxonomy)
    weight: int = Field(ge=1, le=3)
    must_have: bool


class GapRow(Frozen):
    skill: str
    jd_weight: int
    must_have: bool
    evidence: EvidenceLevel
    probe_type: ProbeType
    priority_score: float
    claim_id: str | None = None


class MatchReport(Frozen):
    """How much of what the JD asks for the resume shows, weighted by JD weight."""

    score: float = Field(ge=0, le=1)
    matched: tuple[str, ...]
    missing: tuple[str, ...]


class Rubric(Frozen):
    expected_points: tuple[str, ...]
    red_flags: tuple[str, ...] = ()
    follow_up_hooks: tuple[str, ...] = ()


class PlannedTopic(Frozen):
    id: str
    phase: str
    title: str
    skills: tuple[str, ...]
    priority: TopicPriority
    budget_seconds: int
    min_seconds: int
    max_depth: int
    start_difficulty: int = Field(ge=1, le=4)
    claim_id: str | None = None
    opening_questions: tuple[str, ...] = ()
    rubric: Rubric | None = None


class PhaseBudget(Frozen):
    name: str
    seconds: int
    reserved: bool = False  # never borrowed from (e.g. closing)


class InterviewPlan(Frozen):
    phases: tuple[PhaseBudget, ...]
    topics: tuple[PlannedTopic, ...]


# ------------------------------------------------------------------ live
class TurnSignals(Frozen):
    """Structured output of the Turn Analyzer (LLM). Signals only — never decisions."""

    intent: AnswerIntent
    rubric_points_covered: tuple[str, ...] = ()
    rubric_points_missing: tuple[str, ...] = ()
    coverage_ratio: float = Field(ge=0, le=1)
    specificity: Specificity = Specificity.MEDIUM
    consistency: ClaimConsistency = ClaimConsistency.UNKNOWN
    hooks: tuple[str, ...] = ()
    proposed_follow_up: str | None = None


class TopicProgress(BaseModel):
    topic_id: str
    status: TopicStatus = TopicStatus.PENDING
    used_seconds: int = 0
    depth: int = 0
    scaffold_used: bool = False
    difficulty: int = 2


class Turn(Frozen):
    id: UUID
    interview_id: UUID
    seq: int
    topic_id: str | None
    role: str  # "interviewer" | "candidate"
    text: str
    shown_at: datetime | None = None
    first_keystroke_at: datetime | None = None
    submitted_at: datetime | None = None
    cut_off: bool = False


class PasteEvent(Frozen):
    at_ms: int = Field(ge=0)  # since the question was shown
    chars: int = Field(ge=1)


class Answer(Frozen):
    """One submitted answer plus what the browser saw while it was typed (integrity signals)."""

    question_seq: int = Field(ge=1)  # the question being answered: a double submit is refused
    text: str = Field(min_length=1, max_length=8000)
    first_keystroke_ms: int | None = Field(default=None, ge=0)  # since the question was shown
    idle_ms: int = Field(default=0, ge=0)  # longest pause without typing
    pastes: tuple[PasteEvent, ...] = Field(default=(), max_length=50)


class Draft(Frozen):
    """Autosaved, unsubmitted answer text. Lives in Redis; submitted by the hard stop."""

    question_seq: int = Field(ge=1)
    text: str = Field(max_length=8000)


# ------------------------------------------------------------------ eval
class EvidenceQuote(Frozen):
    turn_seq: int
    quote: str


class DimensionScore(Frozen):
    dimension: str
    level: int = Field(ge=1, le=4)  # anchored scale; converted to /10 by code
    evidence: tuple[EvidenceQuote, ...]


class TopicEvaluation(Frozen):
    topic_id: str
    skills: tuple[str, ...]
    status: TopicStatus
    dimensions: tuple[DimensionScore, ...]
    points_covered: tuple[str, ...] = ()
    points_missed: tuple[str, ...] = ()
    claim_verdict: ClaimVerdict = ClaimVerdict.UNTESTED
    question_count: int = 1
