"""LangGraph state for one live interview. JSON-serialisable so the Postgres checkpointer can
persist it after every node (ADR-0003). Domain objects are stored via model_dump(mode="json")."""

from typing import Any, TypedDict


class InterviewGraphState(TypedDict, total=False):
    interview_id: str
    round_type: str
    company_tier: str
    window: dict[str, Any]  # TimeWindow fields (iso strings)
    plan: dict[str, Any]  # InterviewPlan
    progress: dict[str, dict[str, Any]]  # topic_id -> TopicProgress
    current_topic_id: str | None
    turn_seq: int
    last_question: str
    last_answer: str
    last_signals: dict[str, Any] | None  # TurnSignals
    decision: dict[str, Any] | None  # PolicyDecision
    skill_estimates: dict[str, float]
    answer_seconds: int  # time the candidate spent on the last answer
    system_latency_s: int
    flags: list[str]
    end_reason: str | None
