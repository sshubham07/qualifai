"""Aggregation — anchored levels → /10, topics → skills, with confidence. Pure code."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from qualifai.domain.enums import Confidence, TopicStatus
from qualifai.domain.models import TopicEvaluation

LEVEL_TO_10 = {1: 2.5, 2: 5.0, 3: 7.5, 4: 10.0}


def topic_score(ev: TopicEvaluation) -> float | None:
    """Mean of dimension scores on /10; None when nothing survived the evidence check."""
    if not ev.dimensions:
        return None
    return round(sum(LEVEL_TO_10[d.level] for d in ev.dimensions) / len(ev.dimensions), 2)


def topic_confidence(ev: TopicEvaluation) -> Confidence:
    if ev.status is TopicStatus.PARTIAL or ev.question_count <= 1:
        return Confidence.LOW
    return Confidence.HIGH if ev.question_count >= 3 else Confidence.MEDIUM


@dataclass(frozen=True, slots=True)
class SkillScore:
    skill: str
    score: float  # /10
    confidence: Confidence
    topics: tuple[str, ...]
    questions: int


def aggregate_skills(evaluations: Sequence[TopicEvaluation]) -> dict[str, SkillScore]:
    """skill score = evidence-weighted mean (weight = questions asked) of every topic testing it."""
    acc: dict[str, list[tuple[float, int, str]]] = defaultdict(list)
    for ev in evaluations:
        if ev.status is TopicStatus.NOT_ASSESSED:
            continue
        score = topic_score(ev)
        if score is None:
            continue
        for skill in ev.skills:
            acc[skill].append((score, ev.question_count, ev.topic_id))

    out: dict[str, SkillScore] = {}
    for skill, items in acc.items():
        weight = sum(q for _, q, _ in items)
        mean = sum(s * q for s, q, _ in items) / weight
        conf = (
            Confidence.HIGH if weight >= 4 else Confidence.MEDIUM if weight >= 2 else Confidence.LOW
        )
        out[skill] = SkillScore(
            skill=skill,
            score=round(mean, 2),
            confidence=conf,
            topics=tuple(t for _, _, t in items),
            questions=weight,
        )
    return out
