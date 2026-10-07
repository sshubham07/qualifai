import pytest
from tests.conftest import policy_input, signals

from qualifai.domain.enums import (
    AnswerIntent,
    ClaimConsistency,
    PolicyAction,
    Specificity,
    TimeZone,
)
from qualifai.interview.policy import decide

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("sig", "expected"),
    [
        (signals(coverage_ratio=0.9), PolicyAction.FOLLOW_UP_DEEPER),
        (signals(coverage_ratio=0.5), PolicyAction.CLARIFY_MISSING),
        (signals(coverage_ratio=0.1), PolicyAction.SCAFFOLD),
        (signals(intent=AnswerIntent.DONT_KNOW, coverage_ratio=0.0), PolicyAction.SCAFFOLD),
        (signals(specificity=Specificity.LOW), PolicyAction.PROBE_SPECIFICITY),
        (
            signals(consistency=ClaimConsistency.INFLATED, coverage_ratio=0.9),
            PolicyAction.CHALLENGE_CLAIM,
        ),
        (signals(consistency=ClaimConsistency.CONTRADICTS), PolicyAction.CHALLENGE_CLAIM),
        (signals(intent=AnswerIntent.REDIRECT_ATTEMPT), PolicyAction.REDIRECT_BACK),
        (signals(intent=AnswerIntent.CLARIFICATION_REQUEST), PolicyAction.REPHRASE_QUESTION),
    ],
)
def test_signal_driven_actions_with_spare_time(sig, expected):
    assert decide(policy_input(signals=sig)).action is expected


def test_strong_answer_raises_difficulty():
    assert decide(policy_input(signals=signals(coverage_ratio=0.9))).difficulty_delta == 1


def test_scaffold_only_once_then_move_on():
    d = decide(policy_input(signals=signals(coverage_ratio=0.1), scaffold_used=True))
    assert d.action is PolicyAction.NEXT_TOPIC
    assert d.difficulty_delta == -1


def test_ac2_coverage_guard_blocks_follow_up():
    """AC-2: 6 min left, two unvisited must topics (3 min each) + 2 min closing → no follow-up."""
    d = decide(
        policy_input(
            signals=signals(coverage_ratio=0.95),
            remaining_to_hard_s=6 * 60,
            unvisited_must_min_s=(180, 180),
            next_topic_estimate_s=180,
        )
    )
    assert d.action not in {PolicyAction.FOLLOW_UP_DEEPER, PolicyAction.CLARIFY_MISSING}


def test_topic_budget_exhausted_closes_topic():
    d = decide(policy_input(topic_used_s=300, topic_budget_s=300))
    assert d.action is PolicyAction.CLOSE_TOPIC_TIME


def test_max_depth_moves_on():
    assert decide(policy_input(depth=3, max_depth=3)).action is PolicyAction.NEXT_TOPIC


def test_no_topics_left_wraps_up():
    assert decide(policy_input(depth=3, next_topic_estimate_s=None)).action is PolicyAction.WRAP_UP


@pytest.mark.parametrize(
    ("zone", "action"),
    [(TimeZone.OVERTIME, PolicyAction.WRAP_UP), (TimeZone.EXPIRED, PolicyAction.END)],
)
def test_time_zones_override_signals(zone, action):
    assert decide(policy_input(zone=zone, signals=signals(coverage_ratio=1.0))).action is action


def test_closing_window_only_starts_topics_that_fit():
    d = decide(
        policy_input(
            zone=TimeZone.CLOSING, depth=3, remaining_to_hard_s=7 * 60, next_topic_estimate_s=6 * 60
        )
    )
    assert d.action is PolicyAction.WRAP_UP


def test_last_question_is_announced():
    d = decide(
        policy_input(
            depth=3, remaining_to_hard_s=9 * 60, next_topic_estimate_s=300, unvisited_must_min_s=()
        )
    )
    assert d.action is PolicyAction.NEXT_TOPIC
    assert d.announce_last_question
