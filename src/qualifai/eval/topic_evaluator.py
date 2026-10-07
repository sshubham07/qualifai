"""Per-topic evaluation with the large model. One call per topic thread (opening question +
follow-ups) — not per question (follow-ups depend on each other) and not per interview
(too long for small models, blurry scores)."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence

from qualifai.content.loader import TierPreset
from qualifai.domain.models import PlannedTopic, TopicEvaluation
from qualifai.llm.gateway import LLM
from qualifai.llm.prompts import load_prompt
from qualifai.llm.tasks import LLMTask


async def evaluate_topic(
    llm: LLM, topic: PlannedTopic, transcript: str, tier: TierPreset, claim: str = ""
) -> TopicEvaluation:
    rubric = topic.rubric
    prompt = load_prompt("topic_eval").format(
        tier_name=tier.name,
        tier_guidance=tier.guidance,
        rubric=rubric.model_dump_json(indent=1) if rubric else "{}",
        claim=claim or "none",
        transcript=transcript,
    )
    return await llm.structured(LLMTask.TOPIC_EVAL, "JSON only.", prompt, TopicEvaluation)


async def evaluate_all(
    llm: LLM, items: Sequence[tuple[PlannedTopic, str, str]], tier: TierPreset
) -> list[TopicEvaluation]:
    """items = (topic, topic_transcript, claim_text). Runs in parallel."""
    return list(await asyncio.gather(*(evaluate_topic(llm, t, tx, tier, c) for t, tx, c in items)))
