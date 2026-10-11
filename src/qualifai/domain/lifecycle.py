"""Interview lifecycle state machine — the only place status transitions are allowed."""

from qualifai.domain.enums import InterviewStatus as S
from qualifai.domain.errors import InterviewStateError

ALLOWED: dict[S, frozenset[S]] = {
    S.SUBMITTED: frozenset({S.PREPARING, S.FAILED}),
    S.PREPARING: frozenset({S.READY, S.FAILED}),
    S.READY: frozenset({S.IN_PROGRESS, S.EXPIRED}),
    S.IN_PROGRESS: frozenset({S.COMPLETED}),
    S.COMPLETED: frozenset({S.EVALUATING}),
    S.EVALUATING: frozenset({S.REPORT_READY, S.FAILED}),
    S.FAILED: frozenset(),  # dead end: the reason is stored; trying again is a new interview
    S.REPORT_READY: frozenset(),
    S.EXPIRED: frozenset(),
}


def transition(current: S, target: S) -> S:
    if target not in ALLOWED[current]:
        raise InterviewStateError(f"Cannot move interview from {current} to {target}")
    return target
