"""LangGraph state for one live interview. JSON-serialisable so the Postgres checkpointer can
persist it after every node (ADR-0003). Domain objects are stored via model_dump(mode="json")."""

from typing import Any, TypedDict


class InterviewGraphState(TypedDict, total=False):
    graph_version: int  # an interview finishes on the graph it started on
    interview_id: str
    round_type: str
    company_tier: str
    window: dict[str, Any]  # TimeWindow fields (iso strings)
    plan: dict[str, Any]  # InterviewPlan
    opening_question: str | None  # written in prep; asked first, without a model call
    progress: dict[str, dict[str, Any]]  # topic_id -> TopicProgress
    current_topic_id: str | None
    turn_seq: int
    last_question: str
    last_answer: str
    last_signals: dict[str, Any] | None  # TurnSignals
    decision: dict[str, Any] | None  # PolicyDecision
    skill_estimates: dict[str, float]
    answer_meta: dict[str, Any] | None  # timings + integrity signals of the last answer
    unsaved_answer: bool  # last_answer still has to be written by `closing`
    cut_off: bool  # last_answer is a draft the hard stop submitted
    question_at: str | None  # when the pending question was committed (iso)
    resumed_at: str | None  # when the last answer arrived (iso)
    answer_seconds: int  # time the candidate spent on the last answer
    system_latency_ms: int  # total time the candidate waited on us; becomes latency credit
    flags: list[str]
    end_reason: str | None
