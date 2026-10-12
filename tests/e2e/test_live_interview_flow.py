"""E2E of the live loop: real LangGraph graph + in-memory checkpointer + FakeLLM + FrozenClock.
No network, no Docker. The whole flow over HTTP is in test_http_interview.py."""

from dataclasses import replace
from datetime import UTC, datetime
from itertools import cycle
from typing import Any
from uuid import uuid4

import pytest
from langgraph.checkpoint.memory import MemorySaver

from qualifai.domain.clock import FrozenClock
from qualifai.domain.enums import EndReason, PolicyAction, TopicPriority
from qualifai.domain.models import InterviewPlan, PhaseBudget, PlannedTopic, Rubric, TurnSignals
from qualifai.interview.graph import GRAPH_VERSION, GraphDeps
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
        self.tokens: list[tuple[int, str]] = []
        self.payloads: dict[int, dict[str, Any]] = {}
        self.ended: EndReason | None = None

    async def token(self, interview_id, seq, text):
        self.tokens.append((seq, text))

    async def interviewer_said(self, interview_id, seq, topic_id, text, action, difficulty):
        self.turns.append(("interviewer", seq, topic_id, text))

    async def candidate_said(self, interview_id, seq, topic_id, payload: dict[str, Any]):
        self.turns.append(("candidate", seq, topic_id, payload["text"]))
        self.payloads[seq] = payload

    async def analysed(self, interview_id, seq, signals: TurnSignals, latency_ms):
        pass

    async def completed(self, interview_id, end_reason):
        self.ended = end_reason


def svc_config(interview_id) -> dict[str, Any]:
    return {"configurable": {"thread_id": str(interview_id)}}


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
    return InterviewService(MemorySaver()), deps, sink, clock, llm


async def test_full_interview_ends_naturally_with_follow_ups_bounded_by_depth():
    svc, deps, sink, clock, _ = make([0.9])
    iid = uuid4()
    turn = await svc.start(
        iid, plan(), TimeWindow.for_duration(T0, 45), "r1_technical", "product", deps
    )
    assert turn.question and turn.seq == 1 and turn.phase == "core"
    for _ in range(40):
        clock.advance(150)
        turn = await svc.submit_answer(iid, "A detailed answer", deps)
        if turn.ended:
            break
    assert sink.ended is EndReason.NATURAL and turn.end_reason is EndReason.NATURAL
    assert [seq for _, seq, _, _ in sink.turns] == list(range(1, len(sink.turns) + 1))
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
    turn = await svc.hard_stop(iid, deps)
    assert sink.ended is EndReason.HARD_STOP and turn.end_reason is EndReason.HARD_STOP
    assert "out of time" in sink.turns[-1][3]
    assert [role for role, *_ in sink.turns] == [
        "interviewer",
        "interviewer",
    ]  # no draft, no answer
    assert (await svc.hard_stop(iid, deps)).ended  # a second hard stop finds nothing to do
    assert len(sink.turns) == 2


async def test_hard_stop_submits_the_draft_as_a_cut_off_answer():
    svc, deps, sink, clock, llm = make([0.5])
    iid = uuid4()
    await svc.start(iid, plan(), TimeWindow.for_duration(T0, 45), "r1_technical", "product", deps)
    clock.advance(51 * 60)
    await svc.hard_stop(iid, deps, draft="Half an answ", meta={"submitted_at": "x"})
    assert sink.turns[1] == ("candidate", 2, "t1", "Half an answ")
    assert sink.payloads[2] == {"submitted_at": "x", "text": "Half an answ", "cut_off": True}
    assert sink.turns[2][:2] == ("interviewer", 3) and sink.ended is EndReason.HARD_STOP
    assert LLMTask.TURN_ANALYZER not in [task for task, _ in llm.calls]  # nothing left to decide


async def test_an_answer_after_hard_end_is_kept_and_ends_the_interview_as_a_hard_stop():
    svc, deps, sink, clock, _ = make([0.9])
    iid = uuid4()
    await svc.start(iid, plan(), TimeWindow.for_duration(T0, 45), "r1_technical", "product", deps)
    clock.advance(50 * 60)
    turn = await svc.submit_answer(iid, "Late but complete", deps)
    assert turn.ended and turn.end_reason is EndReason.HARD_STOP
    assert ("candidate", 2, "t1", "Late but complete") in sink.turns


async def test_the_kit_opening_question_is_asked_first_without_a_model_call():
    svc, deps, sink, _, llm = make([0.9])
    turn = await svc.start(
        uuid4(),
        plan(),
        TimeWindow.for_duration(T0, 45),
        "r1_technical",
        "product",
        deps,
        opening_question="Walk me through your platform.",
    )
    assert turn.question == "Walk me through your platform." and llm.calls == []
    assert sink.turns == [("interviewer", 1, "t1", "Walk me through your platform.")]


async def test_questions_are_streamed_token_by_token_before_they_are_committed():
    svc, deps, sink, _, _ = make([0.9])
    await svc.start(
        uuid4(), plan(), TimeWindow.for_duration(T0, 45), "r1_technical", "product", deps
    )
    assert [seq for seq, _ in sink.tokens] == [1, 1, 1]
    assert "".join(t for _, t in sink.tokens).strip() == sink.turns[0][3]


async def test_time_is_measured_by_the_graph_and_slow_turns_become_latency_credit():
    svc, deps, sink, clock, llm = make([0.9])
    slow = llm._responders[LLMTask.QUESTION_GEN]

    def slow_model(system, user):  # the candidate waits 30 s for every question
        clock.advance(30)
        return slow(system, user)

    llm._responders[LLMTask.QUESTION_GEN] = slow_model
    iid = uuid4()
    first = await svc.start(
        iid, plan(), TimeWindow.for_duration(T0, 45), "r1_technical", "product", deps
    )
    assert first.system_latency_s == 0  # nobody was waiting before the first question
    clock.advance(100)
    turn = await svc.submit_answer(iid, "An answer", deps, meta={"idle_ms": 5})
    assert turn.system_latency_s == 30 and sink.payloads[2] == {"idle_ms": 5, "text": "An answer"}
    state = (await svc._graphs[GRAPH_VERSION].aget_state(svc_config(iid))).values
    assert state["progress"]["t1"]["used_seconds"] == 100  # typing time, not our 30 s
    assert state["graph_version"] == GRAPH_VERSION


async def test_the_resume_claim_reaches_the_turn_analyzer():
    svc, deps, _, clock, llm = make([0.9])
    claimed = plan().model_copy(
        update={"topics": (plan().topics[0].model_copy(update={"claim_id": "c1"}),)}
    )
    deps = replace(deps, claims={"c1": "Designed the payments platform"})
    iid = uuid4()
    await svc.start(iid, claimed, TimeWindow.for_duration(T0, 45), "r1_technical", "product", deps)
    clock.advance(60)
    await svc.submit_answer(iid, "I helped a bit", deps)
    analysed = [u for task, u in llm.calls if task is LLMTask.TURN_ANALYZER][-1]
    assert "Designed the payments platform" in analysed


async def test_a_turn_that_died_after_taking_the_answer_is_finished_on_retry():
    svc, deps, sink, clock, llm = make([0.9])
    analyse = llm._responders[LLMTask.TURN_ANALYZER]

    def down(system, user):
        raise ConnectionError("model down")

    iid = uuid4()
    await svc.start(iid, plan(), TimeWindow.for_duration(T0, 45), "r1_technical", "product", deps)
    clock.advance(60)
    llm._responders[LLMTask.TURN_ANALYZER] = down
    with pytest.raises(ConnectionError):
        await svc.submit_answer(iid, "My answer", deps)
    assert sink.turns[-1] == ("candidate", 2, "t1", "My answer")  # committed before the failure

    llm._responders[LLMTask.TURN_ANALYZER] = analyse
    turn = await svc.submit_answer(iid, "My answer", deps)
    assert turn.question and turn.seq == 3
    assert [t for t in sink.turns if t[0] == "candidate"] == [
        ("candidate", 2, "t1", "My answer"),
        ("candidate", 2, "t1", "My answer"),  # the node ran again: the sink must tolerate it
    ]


async def test_policy_not_llm_chooses_actions():
    """The question-generator prompt carries the action chosen by the policy."""
    svc, deps, _, clock, llm = make([0.9])
    iid = uuid4()
    await svc.start(iid, plan(), TimeWindow.for_duration(T0, 45), "r1_technical", "product", deps)
    clock.advance(60)
    await svc.submit_answer(iid, "Strong answer", deps)
    last_gen = [u for task, u in llm.calls if task is LLMTask.QUESTION_GEN][-1]
    assert f"Action: {PolicyAction.FOLLOW_UP_DEEPER.value}" in last_gen
