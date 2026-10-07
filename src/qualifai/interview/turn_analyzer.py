"""Turn Analyzer — the LLM reads one answer and returns *signals* (TurnSignals), never decisions."""

from __future__ import annotations

from qualifai.domain.models import PlannedTopic, TurnSignals
from qualifai.interview.context_compiler import Slice, compile_context
from qualifai.llm.gateway import LLM
from qualifai.llm.prompts import load_prompt
from qualifai.llm.tasks import LLMTask

LIVE_BUDGET_TOKENS = 2000


class TurnAnalyzer:
    def __init__(self, llm: LLM) -> None:
        self._llm = llm

    async def analyze(
        self,
        *,
        topic: PlannedTopic,
        candidate_brief: str,
        round_rules: str,
        recent_turns: str,
        claim_text: str | None,
        answer: str,
    ) -> TurnSignals:
        rubric = topic.rubric
        slices = [
            Slice("Round rules", round_rules, priority=0, static=True),
            Slice("Candidate brief", candidate_brief, priority=1, static=True),
            Slice("Topic", f"{topic.title} (depth target {topic.max_depth})", priority=0),
            Slice(
                "Rubric",
                "\n".join(f"- {p}" for p in (rubric.expected_points if rubric else ())),
                priority=0,
            ),
            Slice("Resume claim", claim_text or "none", priority=2),
            Slice("Recent turns (this topic)", recent_turns, priority=3),
        ]
        context, _dropped = compile_context(slices, LIVE_BUDGET_TOKENS)
        prompt = load_prompt("turn_analyzer").format(context=context, answer=answer)
        return await self._llm.structured(
            LLMTask.TURN_ANALYZER,
            system="You return JSON only.",
            user=prompt,
            schema=TurnSignals,
        )
