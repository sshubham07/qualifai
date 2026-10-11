"""Topic packs — the large model writes opening questions, rubric and follow-up hooks for each
planned topic, grounded in the skill seed bank (and, from V2, retrieved real questions).
Packs are independent, so they are generated in parallel, a few at a time: hosted free tiers cap
tokens per minute, and ten simultaneous calls only produce rate-limit errors."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping

from pydantic import BaseModel

from qualifai.content.loader import RoundTemplate, TierPreset, seed_anchors
from qualifai.domain.models import PlannedTopic, Rubric
from qualifai.llm.gateway import LLM
from qualifai.llm.prompts import load_prompt
from qualifai.llm.tasks import LLMTask

PACK_CONCURRENCY = 2


class TopicPack(BaseModel):
    opening_questions: list[str]
    rubric: Rubric


async def build_pack(
    llm: LLM,
    topic: PlannedTopic,
    template: RoundTemplate,
    tier: TierPreset,
    claim: str = "",
    real_questions: str = "",
) -> PlannedTopic:
    anchors = "\n".join(filter(None, (seed_anchors(s) for s in topic.skills)))
    prompt = load_prompt("topic_pack").format(
        round_name=template.name,
        tier_name=tier.name,
        max_depth=topic.max_depth,
        difficulty=topic.start_difficulty,
        topic_title=topic.title,
        claim=claim or "none",
        jd_skill=", ".join(topic.skills),
        seed_anchors=anchors or "none (unanchored — lower scoring confidence)",
        real_questions=real_questions or "none",
    )
    pack = await llm.structured(LLMTask.TOPIC_PACK, "JSON only.", prompt, TopicPack)
    return topic.model_copy(
        update={"opening_questions": tuple(pack.opening_questions), "rubric": pack.rubric}
    )


async def build_all_packs(
    llm: LLM,
    topics: list[PlannedTopic],
    template: RoundTemplate,
    tier: TierPreset,
    claims: Mapping[str, str],
) -> list[PlannedTopic]:
    """Bounded parallel generation. Progressive readiness (spec-001 FR-9) can await the first N."""
    slots = asyncio.Semaphore(PACK_CONCURRENCY)

    async def one(topic: PlannedTopic) -> PlannedTopic:
        async with slots:
            claim = claims.get(topic.claim_id or "", "")
            return await build_pack(llm, topic, template, tier, claim=claim)

    return list(await asyncio.gather(*(one(t) for t in topics)))
