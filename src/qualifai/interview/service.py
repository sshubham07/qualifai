"""InterviewService — application service the API and workers call for the live phase."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any
from uuid import UUID

from langgraph.types import Command

from qualifai.domain.models import InterviewPlan
from qualifai.interview.graph import GraphDeps
from qualifai.interview.time_window import TimeWindow


def _cfg(interview_id: UUID, deps: GraphDeps) -> dict[str, Any]:
    # thread_id == interview_id → one checkpoint thread per interview
    return {"configurable": {"thread_id": str(interview_id), "deps": deps}}


class InterviewService:
    def __init__(self, graph: Any) -> None:
        self._graph = graph

    async def start(
        self,
        interview_id: UUID,
        plan: InterviewPlan,
        window: TimeWindow,
        round_type: str,
        company_tier: str,
        deps: GraphDeps,
    ) -> str:
        """Run until the first interrupt; returns the first question."""
        state = {
            "interview_id": str(interview_id),
            "round_type": round_type,
            "company_tier": company_tier,
            "window": {
                k: (v.isoformat() if hasattr(v, "isoformat") else v)
                for k, v in asdict(window).items()
            },
            "plan": plan.model_dump(mode="json"),
            "progress": {},
            "turn_seq": 0,
            "system_latency_s": 0,
            "skill_estimates": {},
            "flags": [],
        }
        result = await self._graph.ainvoke(state, _cfg(interview_id, deps))
        question = _pending_question(result)
        if question is None:
            raise RuntimeError("Interview ended before the first question — empty plan?")
        return question

    async def submit_answer(
        self,
        interview_id: UUID,
        text: str,
        answer_seconds: int,
        system_latency_s: int,
        deps: GraphDeps,
    ) -> str | None:
        """Resume the graph with the candidate's answer. Returns next question, or None if ended."""
        payload = {
            "type": "answer",
            "text": text,
            "answer_seconds": answer_seconds,
            "system_latency_s": system_latency_s,
        }
        result = await self._graph.ainvoke(Command(resume=payload), _cfg(interview_id, deps))
        return _pending_question(result)

    async def hard_stop(self, interview_id: UUID, deps: GraphDeps) -> None:
        """Called by the scheduled job at hard_end + grace if the interview is still open."""
        await self._graph.ainvoke(Command(resume={"type": "time_up"}), _cfg(interview_id, deps))


def _pending_question(result: dict[str, Any]) -> str | None:
    interrupts = result.get("__interrupt__") or []
    return interrupts[0].value["question"] if interrupts else None
