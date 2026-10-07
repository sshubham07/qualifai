"""E2E of the live loop: real LangGraph graph + in-memory checkpointer + FakeLLM + FrozenClock.
No network, no Docker. (Full HTTP e2e with Postgres lands with T-27.)"""

from datetime import UTC, datetime
from itertools import cycle
from typing import Any
from uuid import uuid4

import pytest
from langgraph.checkpoint.memory import MemorySaver

from qualifai.domain.clock import FrozenClock
from qualifai.domain.enums import EndReason, PolicyAction, TopicPriority
from qualifai.domain.models import InterviewPlan, PhaseBudget, PlannedTopic, Rubric, TurnSignals
from qualifai.interview.graph import GraphDeps, build_graph
from qualifai.interview.question_generator import QuestionGenerator
from qualifai.interview.service import InterviewService
from qualifai.interview.time_window import TimeWindow
from qualifai.interview.turn_analyzer import TurnAnalyzer
from qualifai.llm.fake import FakeLLM
from qualifai.llm.tasks import LLMTask

pytestmark = pytest.mark.e2e
T0 = datetime(2026, 10, 7, 10, 0, tzinfo=UTC)


class MemorySink:
    def __init__(self) -> None:
        self.turns: list[tuple[str, int, str | None, str]] = []
        self.ended: EndReason | None = None

    async def interviewer_said(self, interview_id, seq, topic_id, text):
        self.turns.append(("interviewer", seq, topic_id, text))

    async def candidate_said(self, interview_id, seq, topic_id, payload: dict[str, Any]):
        self.turns.append(("candidate", seq, topic_id, payload["text"]))

    async def analysed(self, interview_id, seq, signals: TurnSignals):
        pass

    async def completed(self, interview_id, end_reason):
        self.ended = end_reason


def plan() -> InterviewPlan:
    def t(i: int, prio: TopicPriority) -> PlannedTopic:
        return PlannedTopic(
            id=f"t{i}",
            phase="core",
            title=f"topic {i}",
            skills=("kubernetes",),
            priority=prio,
            budget_seconds=420,
            min_seconds=180,
            max_depth=2,
            start_difficulty=2,
            opening_questions=(f"Opening question {i}?",),
            rubric=Rubric(expected_points=("a", "b", "c")),
        )

    return InterviewPlan(
        phases=(
            PhaseBudget(name="core", seconds=2400),
            PhaseBudget(name="closing", seconds=300, reserved=True),
        ),
        topics=(t(1, TopicPriority.MUST), t(2, TopicPriority.MUST), t(3, TopicPriority.SHOULD)),
    )


def make(
    coverages: list[float],
) -> tuple[InterviewService, GraphDeps, MemorySink, FrozenClock, FakeLLM]:
    cov = cycle(coverages)
    llm = FakeLLM(
        {
            LLMTask.TURN_ANALYZER: lambda s, u: {
                "intent": "answer",
                "coverage_ratio": next(cov),
                "specificity": "high",
                "consistency": "consistent",
            },
            LLMTask.QUESTION_GEN: lambda s, u: "Generated interviewer question?",
        }
    )
    sink, clock = MemorySink(), FrozenClock(T0)
    deps = GraphDeps(
        analyzer=TurnAnalyzer(llm),
        generator=QuestionGenerator(llm),
        sink=sink,
        clock=clock,
        round_rules="rules",
        candidate_brief="brief",
        round_name="R1 Technical",
        tier_name="Product-based",
    )
    return InterviewService(build_graph(MemorySaver())), deps, sink, clock, llm


async def test_full_interview_ends_naturally_with_follow_ups_bounded_by_depth():
    svc, deps, sink, clock, _ = make([0.9])
    iid = uuid4()
    q = await svc.start(
        iid, plan(), TimeWindow.for_duration(T0, 45), "r1_technical", "product", deps
    )
    assert q
    for _ in range(40):
        clock.advance(150)
        q = await svc.submit_answer(
            iid, "A detailed answer", answer_seconds=150, system_latency_s=0, deps=deps
        )
        if q is None:
            break
    assert sink.ended is EndReason.NATURAL
    per_topic: dict[str | None, int] = {}
    for role, _, topic, _ in sink.turns:
        if role == "interviewer" and topic:
            per_topic[topic] = per_topic.get(topic, 0) + 1
    # opening + at most max_depth follow-ups per topic
    assert all(n <= 1 + 2 for n in per_topic.values()), per_topic
    assert {"t1", "t2"} <= set(per_topic)  # both must-cover topics were opened


async def test_hard_stop_closes_interview():
    svc, deps, sink, clock, _ = make([0.5])
    iid = uuid4()
    await svc.start(iid, plan(), TimeWindow.for_duration(T0, 45), "r1_technical", "product", deps)
    clock.advance(51 * 60)
    await svc.hard_stop(iid, deps)
    assert sink.ended is EndReason.HARD_STOP
    assert "out of time" in sink.turns[-1][3]


async def test_policy_not_llm_chooses_actions():
    """The question-generator prompt carries the action chosen by the policy."""
    svc, deps, _, clock, llm = make([0.9])
    iid = uuid4()
    await svc.start(iid, plan(), TimeWindow.for_duration(T0, 45), "r1_technical", "product", deps)
    clock.advance(60)
    await svc.submit_answer(iid, "Strong answer", 60, 0, deps)
    last_gen = [u for task, u in llm.calls if task is LLMTask.QUESTION_GEN][-1]
    assert f"Action: {PolicyAction.FOLLOW_UP_DEEPER.value}" in last_gen
