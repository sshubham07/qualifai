"""InterviewService — runs the interview graph: start it, resume it with an answer, stop it.

One checkpoint thread per interview (thread_id == interview_id), so a crash or a redeploy picks
up where the interview was (spec-001 NFR-4). Knows nothing about HTTP or the `interviews` table;
`interview/room.py` is the application service around it."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
from uuid import UUID

from langgraph.types import Command

from qualifai.domain.enums import EndReason
from qualifai.domain.errors import InterviewStateError
from qualifai.domain.models import InterviewPlan
from qualifai.interview.graph import BUILDERS, GRAPH_VERSION, GraphDeps
from qualifai.interview.time_window import TimeWindow


@dataclass(frozen=True, slots=True)
class TurnResult:
    """Where the interview stands after a graph run: a question to show, or the end."""

    question: str | None
    seq: int | None  # turn seq of that question; the answer must name it
    phase: str | None
    final_question: bool
    end_reason: EndReason | None
    system_latency_s: int  # total time the candidate has waited on us so far

    @property
    def ended(self) -> bool:
        return self.question is None


def _cfg(interview_id: UUID, deps: GraphDeps) -> dict[str, Any]:
    # thread_id == interview_id → one checkpoint thread per interview
    return {"configurable": {"thread_id": str(interview_id), "deps": deps}}


def _result(values: dict[str, Any], question: str | None) -> TurnResult:
    topic_id = values.get("current_topic_id")
    topics = (values.get("plan") or {}).get("topics", [])
    phase = next((t["phase"] for t in topics if t["id"] == topic_id), "closing")
    return TurnResult(
        question=question,
        seq=values.get("turn_seq") if question is not None else None,
        phase=phase if question is not None else None,
        final_question=bool(
            topic_id and (values.get("decision") or {}).get("announce_last_question")
        ),
        end_reason=None
        if question is not None
        else EndReason(values.get("end_reason") or EndReason.NATURAL.value),
        system_latency_s=values.get("system_latency_ms", 0) // 1000,
    )


class InterviewService:
    def __init__(self, checkpointer: Any) -> None:
        self._graphs = {version: build(checkpointer) for version, build in BUILDERS.items()}

    async def start(
        self,
        interview_id: UUID,
        plan: InterviewPlan,
        window: TimeWindow,
        round_type: str,
        company_tier: str,
        deps: GraphDeps,
        opening_question: str | None = None,
    ) -> TurnResult:
        """Run until the first interrupt: the first question is waiting for its answer."""
        state = {
            "graph_version": GRAPH_VERSION,
            "interview_id": str(interview_id),
            "round_type": round_type,
            "company_tier": company_tier,
            "window": {
                k: (v.isoformat() if hasattr(v, "isoformat") else v)
                for k, v in asdict(window).items()
            },
            "plan": plan.model_dump(mode="json"),
            "opening_question": opening_question,
            "progress": {},
            "turn_seq": 0,
            "system_latency_ms": 0,
            "skill_estimates": {},
            "flags": [],
        }
        graph = self._graphs[GRAPH_VERSION]
        values = await graph.ainvoke(state, _cfg(interview_id, deps))
        result = _result(values, _pending_question(values))
        if result.ended:
            raise RuntimeError("Interview ended before the first question — empty plan?")
        return result

    async def submit_answer(
        self, interview_id: UUID, text: str, deps: GraphDeps, meta: dict[str, Any] | None = None
    ) -> TurnResult:
        """Resume the graph with the candidate's answer: the next question, or the end."""
        return await self._advance(
            interview_id, {"type": "answer", "text": text, "meta": meta}, deps
        )

    async def hard_stop(
        self,
        interview_id: UUID,
        deps: GraphDeps,
        draft: str = "",
        meta: dict[str, Any] | None = None,
    ) -> TurnResult:
        """Time is up: submit the autosaved draft as a cut-off answer and close the interview."""
        payload = {"type": "time_up", "text": draft, "meta": meta}
        result = await self._advance(interview_id, payload, deps)
        if not result.ended:  # a turn was in flight and has just reached its next question
            result = await self._advance(interview_id, {"type": "time_up", "text": ""}, deps)
        return result

    async def _advance(
        self, interview_id: UUID, payload: dict[str, Any], deps: GraphDeps
    ) -> TurnResult:
        cfg = _cfg(interview_id, deps)
        snapshot = await self._graphs[GRAPH_VERSION].aget_state(cfg)
        version = snapshot.values.get("graph_version", GRAPH_VERSION)
        if version not in self._graphs:
            raise InterviewStateError(f"Interview graph version {version} is no longer supported")
        if not snapshot.next:  # already over (or never started): nothing to resume
            return _result(snapshot.values, None)
        waiting = any(task.interrupts for task in snapshot.tasks)
        # Not waiting: the last run died after taking the answer. Carry on from its checkpoint;
        # the answer is already in the state, so this payload is not needed.
        values = await self._graphs[version].ainvoke(
            Command(resume=payload) if waiting else None, cfg
        )
        return _result(values, _pending_question(values))


def _pending_question(values: dict[str, Any]) -> str | None:
    interrupts = values.get("__interrupt__") or []
    return interrupts[0].value["question"] if interrupts else None
