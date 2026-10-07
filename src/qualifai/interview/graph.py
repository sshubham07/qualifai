"""Live interview loop as a LangGraph state machine (ADR-0003).

Why LangGraph here (and only here): the loop is cyclic, pauses for human input every turn
(`interrupt`) and must survive crashes (Postgres checkpointer). Routing is deterministic —
conditional edges read the PolicyDecision; the LLM never picks an edge.

    START → open_topic → ask → wait_for_answer ─┬─ (answer)  → analyze → decide
                                                └─ (time_up) → closing → END
    decide ─┬─ follow-up action  → ask
            ├─ next / close topic → open_topic
            └─ wrap_up → wait_for_candidate_question → closing → END
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Protocol

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from qualifai.domain.clock import Clock
from qualifai.domain.enums import EndReason, PolicyAction, TimeZone, TopicStatus
from qualifai.domain.models import InterviewPlan, TopicProgress, TurnSignals
from qualifai.interview import policy
from qualifai.interview.question_generator import QuestionGenerator
from qualifai.interview.skill_estimates import clamp_difficulty
from qualifai.interview.state import InterviewGraphState
from qualifai.interview.time_window import TimeWindow
from qualifai.interview.topic_selector import next_topic, unvisited_must_min_seconds
from qualifai.interview.turn_analyzer import TurnAnalyzer

FOLLOW_UP_ACTIONS = {
    PolicyAction.FOLLOW_UP_DEEPER,
    PolicyAction.CLARIFY_MISSING,
    PolicyAction.PROBE_SPECIFICITY,
    PolicyAction.CHALLENGE_CLAIM,
    PolicyAction.SCAFFOLD,
    PolicyAction.REPHRASE_QUESTION,
    PolicyAction.REDIRECT_BACK,
}


class TurnSink(Protocol):
    """Persistence + streaming side effects (Postgres `turns`, SSE). Implemented in services."""

    async def interviewer_said(
        self, interview_id: str, seq: int, topic_id: str | None, text: str
    ) -> None: ...
    async def candidate_said(
        self, interview_id: str, seq: int, topic_id: str | None, payload: dict[str, Any]
    ) -> None: ...
    async def analysed(self, interview_id: str, seq: int, signals: TurnSignals) -> None: ...
    async def completed(self, interview_id: str, end_reason: EndReason) -> None: ...


@dataclass(frozen=True, slots=True)
class GraphDeps:
    analyzer: TurnAnalyzer
    generator: QuestionGenerator
    sink: TurnSink
    clock: Clock
    round_rules: str
    candidate_brief: str
    round_name: str
    tier_name: str


def _deps(config: RunnableConfig) -> GraphDeps:
    return config["configurable"]["deps"]  # type: ignore[no-any-return]


def _window(state: InterviewGraphState) -> TimeWindow:
    w = state["window"]
    return TimeWindow(
        started_at=datetime.fromisoformat(w["started_at"]),
        soft_start_at=datetime.fromisoformat(w["soft_start_at"]),
        target_end_at=datetime.fromisoformat(w["target_end_at"]),
        hard_end_at=datetime.fromisoformat(w["hard_end_at"]),
        latency_credit_s=w.get("latency_credit_s", 0),
    ).with_latency_credit(state.get("system_latency_s", 0))


def _plan(state: InterviewGraphState) -> InterviewPlan:
    return InterviewPlan.model_validate(state["plan"])


def _progress(state: InterviewGraphState) -> dict[str, TopicProgress]:
    return {k: TopicProgress.model_validate(v) for k, v in state.get("progress", {}).items()}


async def _say(
    state: InterviewGraphState,
    deps: GraphDeps,
    action: PolicyAction,
    context: str,
    announce_last: bool = False,
    in_topic: bool = True,
) -> tuple[str, int]:
    text = "".join(
        [
            t
            async for t in deps.generator.phrase(
                action=action,
                round_name=deps.round_name,
                tier_name=deps.tier_name,
                context=context,
                announce_last=announce_last,
            )
        ]
    ).strip()
    seq = state.get("turn_seq", 0) + 1
    topic_id = state.get("current_topic_id") if in_topic else None
    await deps.sink.interviewer_said(state["interview_id"], seq, topic_id, text)
    return text, seq


# ------------------------------------------------------------------ nodes
async def open_topic(state: InterviewGraphState, config: RunnableConfig) -> dict[str, Any]:
    deps = _deps(config)
    plan, progress, window = _plan(state), _progress(state), _window(state)
    usable = window.remaining_to_hard_s(deps.clock.now()) - 120
    topic = next_topic(plan.topics, progress, usable)
    if topic is None:
        return {"current_topic_id": None}
    progress[topic.id] = TopicProgress(
        topic_id=topic.id, status=TopicStatus.ACTIVE, difficulty=topic.start_difficulty
    )
    prev = state.get("decision") or {}
    keep_time_phrasing = prev.get("action") == PolicyAction.CLOSE_TOPIC_TIME.value
    action = PolicyAction.CLOSE_TOPIC_TIME if keep_time_phrasing else PolicyAction.NEXT_TOPIC
    return {
        "current_topic_id": topic.id,
        "progress": {k: v.model_dump(mode="json") for k, v in progress.items()},
        "decision": {
            "action": action.value,
            "announce_last_question": prev.get("announce_last_question", False),
        },
    }


async def ask(state: InterviewGraphState, config: RunnableConfig) -> dict[str, Any]:
    deps = _deps(config)
    decision = state.get("decision") or {}
    action = PolicyAction(decision.get("action", PolicyAction.NEXT_TOPIC.value))
    topic = next(t for t in _plan(state).topics if t.id == state["current_topic_id"])
    context = (
        f"Topic: {topic.title}\nOpening options: {list(topic.opening_questions)}\n"
        f"Last question: {state.get('last_question', '')}\n"
        f"Last answer: {state.get('last_answer', '')}\n"
        f"Hooks: {(state.get('last_signals') or {}).get('hooks', [])}"
    )
    text, seq = await _say(
        state, deps, action, context, decision.get("announce_last_question", False)
    )
    return {"last_question": text, "turn_seq": seq}


def wait_for_answer(state: InterviewGraphState) -> dict[str, Any]:
    # Pauses the graph; resumed by InterviewService.submit_answer / hard_stop with a payload:
    #   {"type": "answer", "text": str, "answer_seconds": int, "system_latency_s": int}
    #   {"type": "time_up"}
    payload: dict[str, Any] = interrupt({"question": state.get("last_question", "")})
    if payload.get("type") == "time_up":
        return {"end_reason": EndReason.HARD_STOP.value}
    return {
        "last_answer": payload["text"],
        "turn_seq": state.get("turn_seq", 0) + 1,
        "system_latency_s": state.get("system_latency_s", 0)
        + int(payload.get("system_latency_s", 0)),
        "answer_seconds": int(payload.get("answer_seconds", 0)),  # consumed by `decide`
    }


async def analyze(state: InterviewGraphState, config: RunnableConfig) -> dict[str, Any]:
    deps = _deps(config)
    topic = next(t for t in _plan(state).topics if t.id == state["current_topic_id"])
    await deps.sink.candidate_said(
        state["interview_id"], state["turn_seq"], topic.id, {"text": state["last_answer"]}
    )
    signals = await deps.analyzer.analyze(
        topic=topic,
        candidate_brief=deps.candidate_brief,
        round_rules=deps.round_rules,
        recent_turns=f"Q: {state.get('last_question', '')}",
        claim_text=None,
        answer=state["last_answer"],
    )
    await deps.sink.analysed(state["interview_id"], state["turn_seq"], signals)
    return {"last_signals": signals.model_dump(mode="json")}


def decide(state: InterviewGraphState, config: RunnableConfig) -> dict[str, Any]:
    deps = _deps(config)
    now = deps.clock.now()
    plan, progress, window = _plan(state), _progress(state), _window(state)
    topic = next(t for t in plan.topics if t.id == state["current_topic_id"])
    prog = progress[topic.id]
    prog.used_seconds += state.get("answer_seconds", 0)
    signals = TurnSignals.model_validate(state["last_signals"])
    remaining = window.remaining_to_hard_s(now)
    upcoming = next_topic(
        plan.topics,
        {**progress, topic.id: prog.model_copy(update={"status": TopicStatus.ASSESSED})},
        remaining,
    )

    d = policy.decide(
        policy.PolicyInput(
            zone=window.zone(now),
            remaining_to_hard_s=remaining,
            signals=signals,
            topic_is_must=topic.priority.value == "must",
            topic_budget_s=topic.budget_seconds,
            topic_used_s=prog.used_seconds,
            depth=prog.depth,
            max_depth=topic.max_depth,
            scaffold_used=prog.scaffold_used,
            unvisited_must_min_s=unvisited_must_min_seconds(
                plan.topics, progress, exclude=topic.id
            ),
            next_topic_estimate_s=upcoming.budget_seconds if upcoming else None,
        )
    )

    if d.action in FOLLOW_UP_ACTIONS:
        prog.depth += 1
        prog.scaffold_used = prog.scaffold_used or d.action is PolicyAction.SCAFFOLD
        prog.difficulty = clamp_difficulty(prog.difficulty + d.difficulty_delta)
    else:
        cut = d.action is PolicyAction.CLOSE_TOPIC_TIME or window.zone(now) is not TimeZone.NORMAL
        prog.status = TopicStatus.PARTIAL if cut and prog.depth == 0 else TopicStatus.ASSESSED
    progress[topic.id] = prog
    return {
        "decision": {
            "action": d.action.value,
            "reason": d.reason,
            "announce_last_question": d.announce_last_question,
        },
        "progress": {k: v.model_dump(mode="json") for k, v in progress.items()},
    }


async def wrap_up(state: InterviewGraphState, config: RunnableConfig) -> dict[str, Any]:
    deps = _deps(config)
    text, seq = await _say(
        state, deps, PolicyAction.WRAP_UP, "Interview is ending.", in_topic=False
    )
    return {"last_question": text, "turn_seq": seq, "current_topic_id": None}


def wait_for_candidate_question(state: InterviewGraphState) -> dict[str, Any]:
    payload: dict[str, Any] = interrupt({"question": state.get("last_question", "")})
    return {"last_answer": payload.get("text", "")}


async def closing(state: InterviewGraphState, config: RunnableConfig) -> dict[str, Any]:
    deps = _deps(config)
    await _say(state, deps, PolicyAction.END, "", in_topic=False)
    reason = EndReason(state.get("end_reason") or EndReason.NATURAL.value)
    await deps.sink.completed(state["interview_id"], reason)
    return {"end_reason": reason.value}


# ------------------------------------------------------------------ routing (deterministic)
def route_after_open(state: InterviewGraphState) -> Literal["ask", "wrap_up"]:
    return "ask" if state.get("current_topic_id") else "wrap_up"


def route_after_wait(state: InterviewGraphState) -> Literal["analyze", "closing"]:
    return "closing" if state.get("end_reason") == EndReason.HARD_STOP.value else "analyze"


def route_after_decide(
    state: InterviewGraphState,
) -> Literal["ask", "open_topic", "wrap_up", "closing"]:
    action = PolicyAction((state.get("decision") or {})["action"])
    if action is PolicyAction.END:
        return "closing"
    if action is PolicyAction.WRAP_UP:
        return "wrap_up"
    if action in FOLLOW_UP_ACTIONS:
        return "ask"
    return "open_topic"


def build_graph(checkpointer: Any = None) -> Any:
    g = StateGraph(InterviewGraphState)
    g.add_node("open_topic", open_topic)
    g.add_node("ask", ask)
    g.add_node("wait_for_answer", wait_for_answer)
    g.add_node("analyze", analyze)
    g.add_node("decide", decide)
    g.add_node("wrap_up", wrap_up)
    g.add_node("wait_for_candidate_question", wait_for_candidate_question)
    g.add_node("closing", closing)

    g.add_edge(START, "open_topic")
    g.add_conditional_edges("open_topic", route_after_open)
    g.add_edge("ask", "wait_for_answer")
    g.add_conditional_edges("wait_for_answer", route_after_wait)
    g.add_edge("analyze", "decide")
    g.add_conditional_edges("decide", route_after_decide)
    g.add_edge("wrap_up", "wait_for_candidate_question")
    g.add_edge("wait_for_candidate_question", "closing")
    g.add_edge("closing", END)
    return g.compile(checkpointer=checkpointer)
