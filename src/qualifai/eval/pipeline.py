"""Evaluation pipeline (worker job). Plain async — a fan-out/fan-in, no cycles (ADR-0003).

per-topic LLM eval (parallel) → evidence check → aggregate → verdict (code)
→ narrative (LLM explains) → Jinja render → store report JSON (source of truth)
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict
from typing import Any

from qualifai.content.loader import TierPreset
from qualifai.domain.enums import ClaimVerdict
from qualifai.domain.models import PlannedTopic, TopicEvaluation
from qualifai.eval.aggregation import aggregate_skills
from qualifai.eval.evidence_check import verify_evaluation
from qualifai.eval.narrative import write_narrative
from qualifai.eval.topic_evaluator import evaluate_all
from qualifai.eval.verdict import JDWeight, VerdictInput, compute_verdict
from qualifai.llm.gateway import LLM


async def evaluate_interview(
    llm: LLM,
    tier: TierPreset,
    topics: Sequence[tuple[PlannedTopic, str, str]],  # (topic, transcript, claim)
    candidate_turns_by_topic: Mapping[str, Mapping[int, str]],
    jd: Mapping[str, JDWeight],
    must_coverage: float,
    integrity_flags: tuple[str, ...] = (),
) -> dict[str, Any]:
    raw = await evaluate_all(llm, topics, tier)
    checked: list[TopicEvaluation] = []
    dropped_total = 0
    for ev in raw:
        rep = verify_evaluation(ev, candidate_turns_by_topic.get(ev.topic_id, {}))
        checked.append(rep.evaluation)
        dropped_total += len(rep.dropped_dimensions)

    skills = aggregate_skills(checked)
    verdict = compute_verdict(
        VerdictInput(
            skills=skills,
            jd=jd,
            must_coverage=must_coverage,
            bands=tier.bands,
            must_have_floor=tier.must_have_floor,
            contradicted_claims=sum(e.claim_verdict is ClaimVerdict.CONTRADICTED for e in checked),
            integrity_flags=integrity_flags,
        )
    )
    aggregate = {
        "verdict": {**asdict(verdict), "band": verdict.band.value, "label": verdict.label.value},
        "skills": [asdict(s) for s in skills.values()],
        "evidence_dropped_dimensions": dropped_total,
    }
    narrative = await write_narrative(llm, aggregate)
    return {
        **aggregate,
        "narrative": narrative.model_dump(),
        "topics": [e.model_dump() for e in checked],
    }
