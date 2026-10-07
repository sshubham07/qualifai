import pytest

from qualifai.domain.enums import TopicPriority, TopicStatus
from qualifai.domain.models import PlannedTopic, TopicProgress
from qualifai.interview.coverage import coverage_ratio, free_seconds
from qualifai.interview.topic_selector import next_topic, unvisited_must_min_seconds

pytestmark = pytest.mark.unit


def topic(tid: str, prio: TopicPriority, budget: int = 300) -> PlannedTopic:
    return PlannedTopic(
        id=tid,
        phase="core",
        title=tid,
        skills=("x",),
        priority=prio,
        budget_seconds=budget,
        min_seconds=180,
        max_depth=3,
        start_difficulty=2,
    )


TOPICS = [
    topic("b1", TopicPriority.BONUS),
    topic("s1", TopicPriority.SHOULD),
    topic("m1", TopicPriority.MUST),
    topic("m2", TopicPriority.MUST),
]


def test_free_seconds_reserves_must_topics_and_closing():
    assert free_seconds(1200, (180, 180), 120) == 720


def test_coverage_ratio():
    assert coverage_ratio(4, 3) == 0.75
    assert coverage_ratio(0, 0) == 1.0


def test_must_first_then_plan_order():
    assert next_topic(TOPICS, {}, 3000).id == "m1"
    progress = {
        "m1": TopicProgress(topic_id="m1", status=TopicStatus.ASSESSED),
        "m2": TopicProgress(topic_id="m2", status=TopicStatus.ASSESSED),
    }
    assert next_topic(TOPICS, progress, 3000).id == "s1"


def test_topic_must_fit():
    assert next_topic(TOPICS, {}, usable_seconds=100) is None


def test_unvisited_must_excludes_current():
    assert unvisited_must_min_seconds(TOPICS, {}, exclude="m1") == (180,)
