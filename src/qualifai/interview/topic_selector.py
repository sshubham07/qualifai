"""Pick the next topic: must → should → bonus, plan order within a tier, and it must fit."""

from collections.abc import Sequence

from qualifai.domain.enums import TopicPriority, TopicStatus
from qualifai.domain.models import PlannedTopic, TopicProgress

_ORDER = {TopicPriority.MUST: 0, TopicPriority.SHOULD: 1, TopicPriority.BONUS: 2}


def next_topic(
    topics: Sequence[PlannedTopic],
    progress: dict[str, TopicProgress],
    usable_seconds: int,
) -> PlannedTopic | None:
    pending = [
        t
        for t in topics
        if progress.get(t.id, TopicProgress(topic_id=t.id)).status is TopicStatus.PENDING
        and t.min_seconds <= usable_seconds
    ]
    if not pending:
        return None
    index = {t.id: i for i, t in enumerate(topics)}
    return min(pending, key=lambda t: (_ORDER[t.priority], index[t.id]))


def unvisited_must_min_seconds(
    topics: Sequence[PlannedTopic], progress: dict[str, TopicProgress], exclude: str | None = None
) -> tuple[int, ...]:
    return tuple(
        t.min_seconds
        for t in topics
        if t.priority is TopicPriority.MUST
        and t.id != exclude
        and progress.get(t.id, TopicProgress(topic_id=t.id)).status is TopicStatus.PENDING
    )
