"""SQLAlchemy 2.0 tables. `turns` is append-only: past questions/answers are never updated."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

JSONType = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    pass


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base, Timestamped):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)


class Interview(Base, Timestamped):
    __tablename__ = "interviews"
    id: Mapped[UUID] = mapped_column(primary_key=True)  # UUIDv7 (time-ordered)
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"), index=True
    )  # no email → None
    status: Mapped[str] = mapped_column(String(32), index=True)
    round_type: Mapped[str] = mapped_column(String(32))
    company_tier: Mapped[str] = mapped_column(String(32))
    role_family: Mapped[str] = mapped_column(String(32))
    support_level: Mapped[str | None] = mapped_column(String(16))  # set by the intake gate
    target_minutes: Mapped[int] = mapped_column(Integer)
    resume_text: Mapped[str | None] = mapped_column(Text)  # nulled after completion / expiry
    jd_text: Mapped[str] = mapped_column(Text)
    experience_min_years: Mapped[int] = mapped_column(Integer)
    experience_max_years: Mapped[int] = mapped_column(Integer)
    company_name: Mapped[str | None] = mapped_column(String(200))
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    soft_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    target_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    hard_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    latency_credit_s: Mapped[int] = mapped_column(Integer, default=0)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_reason: Mapped[str | None] = mapped_column(String(32))
    failure_code: Mapped[str | None] = mapped_column(String(32))  # FailureCode when FAILED
    failure_reason: Mapped[str | None] = mapped_column(Text)  # the sentence shown to the candidate
    access_token_hash: Mapped[str | None] = mapped_column(String(128))  # magic-link fallback


class InterviewKit(Base, Timestamped):
    __tablename__ = "interview_kits"
    interview_id: Mapped[UUID] = mapped_column(ForeignKey("interviews.id"), primary_key=True)
    profile: Mapped[dict[str, Any]] = mapped_column(JSONType)  # claims, jd skills, gap matrix
    plan: Mapped[dict[str, Any]] = mapped_column(JSONType)  # InterviewPlan incl. topic packs
    prep_progress: Mapped[list[str]] = mapped_column(JSONType, default=list)


class TurnRow(Base):
    __tablename__ = "turns"
    __table_args__ = (UniqueConstraint("interview_id", "seq"),)
    id: Mapped[UUID] = mapped_column(primary_key=True)
    interview_id: Mapped[UUID] = mapped_column(ForeignKey("interviews.id"), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    topic_id: Mapped[str | None] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(16))  # interviewer | candidate
    text: Mapped[str] = mapped_column(Text)
    action_type: Mapped[str | None] = mapped_column(String(32))
    difficulty: Mapped[int | None] = mapped_column(Integer)
    shown_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_keystroke_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cut_off: Mapped[bool] = mapped_column(Boolean, default=False)


class TurnAnalysis(Base):
    __tablename__ = "turn_analyses"
    turn_id: Mapped[UUID] = mapped_column(ForeignKey("turns.id"), primary_key=True)
    signals: Mapped[dict[str, Any]] = mapped_column(JSONType)
    model: Mapped[str] = mapped_column(String(128))
    latency_ms: Mapped[int] = mapped_column(Integer)


class TopicSummary(Base):
    __tablename__ = "topic_summaries"
    interview_id: Mapped[UUID] = mapped_column(ForeignKey("interviews.id"), primary_key=True)
    topic_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(16))
    summary: Mapped[str] = mapped_column(Text)
    used_seconds: Mapped[int] = mapped_column(Integer)


class InterviewEvent(Base, Timestamped):
    __tablename__ = "interview_events"
    __table_args__ = (Index("ix_events_interview_type", "interview_id", "type"),)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    interview_id: Mapped[UUID] = mapped_column(ForeignKey("interviews.id"))
    type: Mapped[str] = mapped_column(String(48))  # paste | idle | nudge | reconnect | ...
    payload: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)


class Evaluation(Base, Timestamped):
    __tablename__ = "evaluations"
    interview_id: Mapped[UUID] = mapped_column(ForeignKey("interviews.id"), primary_key=True)
    topic_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    result: Mapped[dict[str, Any]] = mapped_column(JSONType)
    model: Mapped[str] = mapped_column(String(128))


class Report(Base, Timestamped):
    __tablename__ = "reports"
    interview_id: Mapped[UUID] = mapped_column(ForeignKey("interviews.id"), primary_key=True)
    report: Mapped[dict[str, Any]] = mapped_column(JSONType)  # source of truth; HTML is derived
    html_object_key: Mapped[str | None] = mapped_column(String(512))


class DemandLog(Base, Timestamped):
    """Unsupported roles / unknown skills — tells us which content to write next."""

    __tablename__ = "demand_log"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(32))  # role_family | skill
    value: Mapped[str] = mapped_column(String(128), index=True)
