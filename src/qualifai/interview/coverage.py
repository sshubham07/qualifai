"""Coverage guard: follow-ups may only spend *spare* time, never must-cover time.

free = remaining - sum(min time of unvisited must-cover topics) - closing reserve
"""

from collections.abc import Iterable


def free_seconds(
    remaining_s: int,
    unvisited_must_min_s: Iterable[int],
    closing_reserve_s: int,
) -> int:
    return remaining_s - sum(unvisited_must_min_s) - closing_reserve_s


def coverage_ratio(must_total: int, must_opened: int) -> float:
    """Share of must-cover topics that were at least opened (used by the verdict coverage gate)."""
    return 1.0 if must_total == 0 else must_opened / must_total
