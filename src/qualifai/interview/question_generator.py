"""Question Generator — phrases the action the policy already chose. Some actions use fixed
templates (no LLM) so the interview can always end cleanly even if the model is down."""

from __future__ import annotations

from collections.abc import AsyncIterator

from qualifai.domain.enums import PolicyAction
from qualifai.llm.gateway import LLM
from qualifai.llm.prompts import load_prompt
from qualifai.llm.tasks import LLMTask

ACTION_GUIDANCE: dict[PolicyAction, str] = {
    PolicyAction.FOLLOW_UP_DEEPER: "Go one level deeper on what they just said (mechanism, "
    "failure mode, scale or trade-off).",
    PolicyAction.CLARIFY_MISSING: "Ask about ONE important missing point without hinting "
    "the answer.",
    PolicyAction.PROBE_SPECIFICITY: "Ask what exactly THEY did / configured / measured.",
    PolicyAction.CHALLENGE_CLAIM: "Politely point out the gap between the resume claim and the "
    "answer and ask them to reconcile it.",
    PolicyAction.SCAFFOLD: "Rephrase more simply or give a small concrete scenario. No answers.",
    PolicyAction.REPHRASE_QUESTION: "Clarify the previous question. Do not give the answer.",
    PolicyAction.REDIRECT_BACK: "Briefly and politely steer back to the previous question.",
    PolicyAction.NEXT_TOPIC: "Acknowledge briefly, then open the next topic with its "
    "opening question.",
    PolicyAction.CLOSE_TOPIC_TIME: "Say you'd like to move on for time, then open the next topic.",
    PolicyAction.WRAP_UP: "Thank the candidate and invite one question from them about the role.",
}

FIXED_TEMPLATES: dict[PolicyAction, str] = {
    PolicyAction.END: "We're out of time — thank you for your answers. "
    "Your detailed report will be ready shortly.",
}


class QuestionGenerator:
    def __init__(self, llm: LLM) -> None:
        self._llm = llm

    async def phrase(
        self,
        *,
        action: PolicyAction,
        round_name: str,
        tier_name: str,
        context: str,
        announce_last: bool = False,
    ) -> AsyncIterator[str]:
        if action in FIXED_TEMPLATES:
            yield FIXED_TEMPLATES[action]
            return
        time_note = (
            "Mention naturally that this is the final technical question." if announce_last else ""
        )
        prompt = load_prompt("question_gen").format(
            round_name=round_name,
            tier_name=tier_name,
            action=action.value,
            action_guidance=ACTION_GUIDANCE[action],
            time_note=time_note,
            context=context,
        )
        async for token in self._llm.stream(LLMTask.QUESTION_GEN, system="", user=prompt):
            yield token
