"""Request/response DTOs (separate from domain models on purpose)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from qualifai.domain.enums import InterviewStatus


class InterviewAccepted(BaseModel):
    interview_id: UUID
    status: InterviewStatus
    detected_role: str
    support: str


class InterviewStatusOut(BaseModel):
    interview_id: UUID
    status: InterviewStatus
    progress: list[str] = []
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
