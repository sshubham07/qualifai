"""The interview room — the application service behind POST /start, POST /answers and the
hard-stop job (spec-001 T-22..T-24).

It owns the `interviews` row: who may start, the lifecycle transition, the time window, the
latency credit and the end. The questioning itself is the graph's job (`InterviewService`).

One interview is worked on by one caller at a time: each function first locks the row, so a
double submit or a hard stop arriving mid-answer waits its turn and then sees the new state."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Protocol
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qualifai.content.loader import round_template, tier_preset
from qualifai.db.models import Interview, InterviewKit, TurnRow
from qualifai.domain.clock import Clock
from qualifai.domain.enums import CompanyTier, InterviewStatus, RoundType
from qualifai.domain.errors import InterviewNotFound, InterviewStateError, NotInterviewOwner
from qualifai.domain.lifecycle import transition
from qualifai.domain.models import Answer, Draft, Frozen, InterviewPlan
from qualifai.domain.tokens import token_matches
from qualifai.interview.graph import GraphDeps, TurnSink
from qualifai.interview.question_generator import QuestionGenerator
from qualifai.interview.service import InterviewService, TurnResult
from qualifai.interview.time_window import TimeWindow
from qualifai.interview.turn_analyzer import TurnAnalyzer
from qualifai.llm.gateway import LLM

log = structlog.get_logger(__name__)
BRIEF_CLAIMS = 5


class Drafts(Protocol):
    async def save(self, interview_id: UUID, draft: Draft) -> None: ...
    async def load(self, interview_id: UUID) -> Draft | None: ...
    async def clear(self, interview_id: UUID) -> None: ...


@dataclass(frozen=True, slots=True)
class RoomDeps:
    session: AsyncSession
    service: InterviewService
    llm: LLM
    sink: TurnSink
    clock: Clock
    drafts: Drafts
    schedule_hard_stop: Callable[[UUID, datetime], Awaitable[None]]
    enqueue_evaluation: Callable[[UUID], Awaitable[None]]
    hard_stop_grace_s: int


class RoomTurn(Frozen):
    """What the page needs after each step: the question to show, or that it is over."""

    question: str | None
    seq: int | None
    ended: bool
    phase: str | None = None
    final_question: bool = False
    draft: str | None = None  # only when rejoining
    started_at: datetime
    target_end_at: datetime  # moves with the latency credit; the page shows elapsed / ~target


async def _locked(session: AsyncSession, interview_id: UUID) -> Interview | None:
    # FOR NO KEY UPDATE: callers queue up here, while the sink's own sessions can still insert
    # turns that reference this row.
    return await session.get(
        Interview, interview_id, with_for_update={"key_share": True}, populate_existing=True
    )


async def _last_turn(session: AsyncSession, interview_id: UUID) -> TurnRow | None:
    return await session.scalar(
        select(TurnRow)
        .where(TurnRow.interview_id == interview_id)
        .order_by(TurnRow.seq.desc())
        .limit(1)
    )


def _window(interview: Interview, system_latency_s: int | None = None) -> TimeWindow:
    """The stored window, shifted by the latency credit (stored, or recomputed from a new total)."""
    assert interview.started_at and interview.soft_start_at
    assert interview.target_end_at and interview.hard_end_at
    base = TimeWindow(
        started_at=interview.started_at,
        soft_start_at=interview.soft_start_at,
        target_end_at=interview.target_end_at,
        hard_end_at=interview.hard_end_at,
    )
    if system_latency_s is not None:
        return base.with_latency_credit(system_latency_s)
    return base.with_latency_credit(interview.latency_credit_s, threshold_s=0)


def _brief(interview: Interview, kit: InterviewKit) -> str:
    """A few lines about the candidate for the live prompts — never the whole resume."""
    years = kit.profile.get("resume_years")
    lines = [
        f"Applying for a role asking {interview.experience_min_years}–"
        f"{interview.experience_max_years} years; resume shows "
        f"{years if years is not None else 'an unstated number of'} years."
    ]
    lines += [f"- {c['text']}" for c in kit.profile.get("claims", [])[:BRIEF_CLAIMS]]
    return "\n".join(lines)


def _graph_deps(deps: RoomDeps, interview: Interview, kit: InterviewKit) -> GraphDeps:
    template = round_template(RoundType(interview.round_type))
    return GraphDeps(
        analyzer=TurnAnalyzer(deps.llm),
        generator=QuestionGenerator(deps.llm),
        sink=deps.sink,
        clock=deps.clock,
        round_rules=template.rules,
        candidate_brief=_brief(interview, kit),
        round_name=template.name,
        tier_name=tier_preset(CompanyTier(interview.company_tier)).name,
        claims={c["id"]: c["text"] for c in kit.profile.get("claims", [])},
    )


def _turn(interview: Interview, result: TurnResult, draft: str | None = None) -> RoomTurn:
    assert interview.started_at
    return RoomTurn(
        question=result.question,
        seq=result.seq,
        ended=result.ended,
        phase=result.phase,
        final_question=result.final_question,
        draft=draft,
        started_at=interview.started_at,
        target_end_at=_window(interview).target_end_at,
    )


async def _settle(deps: RoomDeps, interview: Interview, result: TurnResult) -> RoomTurn:
    """Write what the graph run changed on the interview: the latency credit, and the end."""
    interview.latency_credit_s = _window(interview, result.system_latency_s).latency_credit_s
    if result.ended:
        interview.status = transition(
            InterviewStatus(interview.status), InterviewStatus.COMPLETED
        ).value
        interview.ended_at = deps.clock.now()
        interview.end_reason = result.end_reason.value if result.end_reason else None
    await deps.session.commit()
    if result.ended:
        await deps.drafts.clear(interview.id)
        try:  # the interview is safely over either way; evaluation can be enqueued again
            await deps.enqueue_evaluation(interview.id)
        except Exception:
            log.exception("room.enqueue_evaluation_failed", interview_id=str(interview.id))
    return _turn(interview, result)


def _check_owner(interview: Interview, token: str | None) -> None:
    """An emailed interview needs its link's token. Without an email the meet id is all there
    is to check (ADR-0017)."""
    expected = interview.access_token_hash
    if expected and not token_matches(token, expected):
        raise NotInterviewOwner(
            "This interview was sent to an email address: open it from that link"
        )


async def start_interview(deps: RoomDeps, interview_id: UUID, token: str | None = None) -> RoomTurn:
    """READY → IN_PROGRESS: set the time window, schedule the hard stop, ask the first question."""
    interview = await _locked(deps.session, interview_id)
    if interview is None:
        raise InterviewNotFound(str(interview_id))
    _check_owner(interview, token)
    now = deps.clock.now()
    # One attempt per kit: anything but READY (started, finished, failed, expired) is refused.
    status = transition(InterviewStatus(interview.status), InterviewStatus.IN_PROGRESS)
    if interview.expires_at and interview.expires_at <= now:
        raise InterviewStateError("This interview has expired")

    kit = await deps.session.get_one(InterviewKit, interview_id)
    window = TimeWindow.for_duration(now, interview.target_minutes)
    result = await deps.service.start(
        interview_id,
        InterviewPlan.model_validate(kit.plan),
        window,
        interview.round_type,
        interview.company_tier,
        _graph_deps(deps, interview, kit),
        opening_question=kit.profile.get("opening_question"),
    )
    interview.status = status.value
    interview.started_at = window.started_at
    interview.soft_start_at = window.soft_start_at
    interview.target_end_at = window.target_end_at
    interview.hard_end_at = window.hard_end_at
    # Scheduled before the commit: a job for an interview that never started does nothing,
    # an interview without its hard stop would never end.
    await deps.schedule_hard_stop(
        interview_id, window.hard_end_at + timedelta(seconds=deps.hard_stop_grace_s)
    )
    await deps.session.commit()
    return _turn(interview, result)


def _meta(question: TurnRow, answer: Answer | None, now: datetime) -> dict[str, Any]:
    """Timings for the candidate turn. The browser only reports offsets; the clock is ours."""
    shown = question.shown_at
    meta: dict[str, Any] = {
        "shown_at": shown.isoformat() if shown else None,
        "submitted_at": now.isoformat(),
    }
    if answer is None:
        return meta
    first = answer.first_keystroke_ms
    return {
        **meta,
        "first_keystroke_at": (shown + timedelta(milliseconds=first)).isoformat()
        if shown and first is not None
        else None,
        "first_keystroke_ms": first,
        "idle_ms": answer.idle_ms,
        "pastes": [p.model_dump() for p in answer.pastes],
    }


async def submit_answer(deps: RoomDeps, interview_id: UUID, answer: Answer) -> RoomTurn:
    interview = await _locked(deps.session, interview_id)
    if interview is None:
        raise InterviewNotFound(str(interview_id))
    if interview.status != InterviewStatus.IN_PROGRESS:
        raise InterviewStateError("This interview is not in progress")
    last = await _last_turn(deps.session, interview_id)
    if last is None:
        raise InterviewStateError("This interview has no question to answer")
    asked = last.role == "interviewer" and last.seq == answer.question_seq
    # The answer was committed but its turn died before the next question: finish that turn.
    retried = last.role == "candidate" and last.seq == answer.question_seq + 1
    if not (asked or retried):
        raise InterviewStateError("That question has already been answered")

    kit = await deps.session.get_one(InterviewKit, interview_id)
    result = await deps.service.submit_answer(
        interview_id,
        answer.text,
        _graph_deps(deps, interview, kit),
        meta=_meta(last, answer, deps.clock.now()),
    )
    await deps.drafts.clear(interview_id)  # the answer is committed: the draft is history
    return await _settle(deps, interview, result)


async def hard_stop(deps: RoomDeps, interview_id: UUID) -> None:
    """The scheduled end. Does nothing if the interview is already over; waits again if the
    latency credit has moved hard_end; otherwise submits the draft and closes the interview."""
    interview = await _locked(deps.session, interview_id)
    if interview is None or interview.status != InterviewStatus.IN_PROGRESS:
        return
    now = deps.clock.now()
    due = _window(interview).hard_end_at + timedelta(seconds=deps.hard_stop_grace_s)
    if now < due:
        await deps.schedule_hard_stop(interview_id, due)
        return

    last = await _last_turn(deps.session, interview_id)
    draft = await deps.drafts.load(interview_id)
    pending = last is not None and last.role == "interviewer"
    text = draft.text if draft and pending and last and draft.question_seq == last.seq else ""
    kit = await deps.session.get_one(InterviewKit, interview_id)
    result = await deps.service.hard_stop(
        interview_id,
        _graph_deps(deps, interview, kit),
        draft=text,
        meta=_meta(last, None, now) if last else None,
    )
    await _settle(deps, interview, result)
    log.info("room.hard_stop", interview_id=str(interview_id), draft_submitted=bool(text.strip()))


async def save_draft(deps: RoomDeps, interview_id: UUID, draft: Draft) -> None:
    interview = await deps.session.get(Interview, interview_id)
    if interview is None:
        raise InterviewNotFound(str(interview_id))
    if interview.status != InterviewStatus.IN_PROGRESS:
        raise InterviewStateError("This interview is not in progress")
    await deps.drafts.save(interview_id, draft)


async def rejoin(deps: RoomDeps, interview_id: UUID) -> RoomTurn:
    """The pending question and the autosaved draft, for a page that was reloaded mid-interview."""
    interview = await deps.session.get(Interview, interview_id)
    if interview is None:
        raise InterviewNotFound(str(interview_id))
    if interview.started_at is None:
        raise InterviewStateError("This interview has not started")
    last = await _last_turn(deps.session, interview_id)
    live = interview.status == InterviewStatus.IN_PROGRESS
    pending = last if live and last and last.role == "interviewer" else None
    draft = await deps.drafts.load(interview_id) if pending else None
    return RoomTurn(
        question=pending.text if pending else None,
        seq=pending.seq if pending else None,
        ended=not live,
        phase=None,
        draft=draft.text if draft and pending and draft.question_seq == pending.seq else None,
        started_at=interview.started_at,
        target_end_at=_window(interview).target_end_at,
    )
