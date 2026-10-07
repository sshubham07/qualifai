"""Policy Engine — decides the next action. Pure Python: "LLM proposes, policy disposes" (ADR-0002).

Inputs are *signals* (from the Turn Analyzer) plus *facts* (time, budgets, coverage).
The output is an action the Question Generator only has to phrase.
This module must never import an LLM, LangGraph or the DB (enforced by import-linter).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from qualifai.domain.enums import (
    AnswerIntent,
    ClaimConsistency,
    PolicyAction,
    Specificity,
    TimeZone,
)
from qualifai.domain.models import TurnSignals
from qualifai.interview.coverage import free_seconds

STRONG_COVERAGE = 0.7
PARTIAL_COVERAGE = 0.3


@dataclass(frozen=True, slots=True)
class PolicyInput:
    zone: TimeZone
    remaining_to_hard_s: int
    signals: TurnSignals
    topic_is_must: bool
    topic_budget_s: int
    topic_used_s: int
    depth: int
    max_depth: int
    scaffold_used: bool
    unvisited_must_min_s: tuple[int, ...]
    next_topic_estimate_s: int | None  # None => no topics left
    closing_reserve_s: int = 120
    follow_up_estimate_s: int = 150
    min_topic_s: int = 180


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    action: PolicyAction
    reason: str
    difficulty_delta: int = 0
    announce_last_question: bool = False
    notes: tuple[str, ...] = field(default_factory=tuple)


def decide(p: PolicyInput) -> PolicyDecision:
    s = p.signals

    # 1. Hard time limits always win.
    if p.zone is TimeZone.EXPIRED:
        return PolicyDecision(PolicyAction.END, "hard_end reached")
    if p.zone is TimeZone.OVERTIME:
        return PolicyDecision(PolicyAction.WRAP_UP, "past target_end: no new questions")

    # 2. Conversation control — the interviewer stays in charge.
    if s.intent is AnswerIntent.REDIRECT_ATTEMPT:
        return PolicyDecision(PolicyAction.REDIRECT_BACK, "candidate tried to steer the interview")
    if s.intent is AnswerIntent.CLARIFICATION_REQUEST:
        return PolicyDecision(PolicyAction.REPHRASE_QUESTION, "candidate asked for clarification")

    free = free_seconds(p.remaining_to_hard_s, p.unvisited_must_min_s, p.closing_reserve_s)
    over_budget = p.topic_used_s >= p.topic_budget_s
    can_follow_up = p.depth < p.max_depth and not over_budget and free >= p.follow_up_estimate_s

    # 3. Signal-driven follow-ups (only with spare time).
    if can_follow_up:
        if s.consistency in (ClaimConsistency.CONTRADICTS, ClaimConsistency.INFLATED):
            return PolicyDecision(PolicyAction.CHALLENGE_CLAIM, f"claim {s.consistency}")
        if s.intent is AnswerIntent.DONT_KNOW or s.coverage_ratio < PARTIAL_COVERAGE:
            if not p.scaffold_used:
                return PolicyDecision(PolicyAction.SCAFFOLD, "weak answer: one scaffold", -1)
            return _move_on(p, "weak after scaffold", difficulty_delta=-1)
        if s.specificity is Specificity.LOW:
            return PolicyDecision(PolicyAction.PROBE_SPECIFICITY, "vague / buzzword answer")
        if s.coverage_ratio >= STRONG_COVERAGE:
            return PolicyDecision(PolicyAction.FOLLOW_UP_DEEPER, "strong answer: go deeper", +1)
        return PolicyDecision(PolicyAction.CLARIFY_MISSING, "partial answer: probe a missing point")

    # 4. No spare time / depth / budget for this topic → move on or close.
    delta = -1 if (s.intent is AnswerIntent.DONT_KNOW) else 0
    if over_budget:
        return _move_on(p, "topic budget used", PolicyAction.CLOSE_TOPIC_TIME, delta)
    return _move_on(p, "depth or spare time exhausted", difficulty_delta=delta)


def _move_on(
    p: PolicyInput,
    reason: str,
    action: PolicyAction = PolicyAction.NEXT_TOPIC,
    difficulty_delta: int = 0,
) -> PolicyDecision:
    if p.next_topic_estimate_s is None:
        return PolicyDecision(PolicyAction.WRAP_UP, f"{reason}; no topics left")

    usable = p.remaining_to_hard_s - p.closing_reserve_s
    if usable < min(p.next_topic_estimate_s, p.min_topic_s):
        return PolicyDecision(PolicyAction.WRAP_UP, f"{reason}; next topic doesn't fit")

    # In the closing window only start a topic that fully fits before hard_end.
    if p.zone is TimeZone.CLOSING and usable < p.next_topic_estimate_s:
        return PolicyDecision(PolicyAction.WRAP_UP, f"{reason}; closing window")

    is_last = usable - p.next_topic_estimate_s < p.min_topic_s
    return PolicyDecision(action, reason, difficulty_delta, announce_last_question=is_last)
