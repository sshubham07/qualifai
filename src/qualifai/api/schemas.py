"""Request/response DTOs (separate from domain models on purpose)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from qualifai.content.loader import round_template
from qualifai.domain.enums import InterviewStatus, RoundType
from qualifai.domain.models import InterviewRequest


class InterviewIn(InterviewRequest):
    """POST /v1/interviews body: the interview request, plus an optional email for the link."""

    email: str | None = Field(default=None, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    round_type: RoundType = RoundType.R1_TECHNICAL  # the interview focus; R1 is "general"

    @model_validator(mode="before")
    @classmethod
    def _length_from_the_round(cls, data: object) -> object:
        """No `target_minutes` given → the chosen round's own length (content/rounds/*.yaml)."""
        if not isinstance(data, dict) or data.get("target_minutes") is not None:
            return data
        try:
            round_type = RoundType(data.get("round_type", RoundType.R1_TECHNICAL))
        except ValueError:
            return data  # the field's own validation reports the unknown round
        return {**data, "target_minutes": round_template(round_type).default_minutes}

    @field_validator("email", mode="before")
    @classmethod
    def _normalise_email(cls, v: object) -> object:
        return v.strip().lower() if isinstance(v, str) else v

    def to_request(self) -> InterviewRequest:
        return InterviewRequest(**self.model_dump(exclude={"email"}))


class InterviewAccepted(BaseModel):
    meet_id: UUID  # the interview id; what the candidate keeps to check back
    status: InterviewStatus


class InterviewStatusOut(BaseModel):
    meet_id: UUID
    status: InterviewStatus
    round_type: RoundType
    target_minutes: int
    detected_role: str | None = None  # known once the intake gate has run
    support: str | None = None
    failure_code: str | None = None
    failure_reason: str | None = None
    progress: list[str] = []  # prep steps started so far; while PREPARING the last is running
    opening_question: str | None = None  # READY only; moves behind POST /start with T-22
    expires_at: datetime | None = None
    started_at: datetime | None = None
    target_end_at: datetime | None = None
    server_now: datetime


class AnswerIn(BaseModel):
    text: str = Field(max_length=8000)
    shown_at: datetime
    first_keystroke_at: datetime | None = None
    submitted_at: datetime
    pasted: bool = False


class NextQuestionOut(BaseModel):
    question: str | None
    ended: bool
    phase: str | None = None
    final_question: bool = False
