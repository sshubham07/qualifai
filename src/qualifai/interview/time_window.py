"""Flexible interview time window (ADR-0012).

An interview of "about 45 minutes" is modelled as three markers instead of one deadline:

    soft_start (40)  ->  target_end (45)  ->  hard_end (50)

The policy reads the zone and asks "does the next item fit before hard_end?".
Pure and deterministic: callers pass `now` explicitly, which keeps it trivially testable.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from qualifai.domain.enums import TimeZone

# target minutes -> (soft_start, target_end, hard_end)
DURATION_PRESETS: dict[int, tuple[int, int, int]] = {
    30: (27, 30, 33),
    45: (40, 45, 50),
    60: (55, 60, 65),
}
MAX_LATENCY_CREDIT_S = 180


def _derive(target_min: int) -> tuple[int, int, int]:
    if target_min in DURATION_PRESETS:
        return DURATION_PRESETS[target_min]
    slack = max(3, round(target_min * 0.1))
    return target_min - slack, target_min, target_min + slack


@dataclass(frozen=True, slots=True)
class TimeWindow:
    started_at: datetime
    soft_start_at: datetime
    target_end_at: datetime
    hard_end_at: datetime
    latency_credit_s: int = 0

    @classmethod
    def for_duration(cls, started_at: datetime, target_minutes: int) -> TimeWindow:
        soft, target, hard = _derive(target_minutes)
        return cls(
            started_at=started_at,
            soft_start_at=started_at + timedelta(minutes=soft),
            target_end_at=started_at + timedelta(minutes=target),
            hard_end_at=started_at + timedelta(minutes=hard),
        )

    def with_latency_credit(self, total_system_latency_s: int, threshold_s: int = 2) -> TimeWindow:
        """Shift the whole window by slow-system time so candidates aren't penalised (capped)."""
        credit = min(max(total_system_latency_s - threshold_s, 0), MAX_LATENCY_CREDIT_S)
        delta = timedelta(seconds=credit - self.latency_credit_s)
        return replace(
            self,
            soft_start_at=self.soft_start_at + delta,
            target_end_at=self.target_end_at + delta,
            hard_end_at=self.hard_end_at + delta,
            latency_credit_s=credit,
        )

    def zone(self, now: datetime) -> TimeZone:
        if now >= self.hard_end_at:
            return TimeZone.EXPIRED
        if now >= self.target_end_at:
            return TimeZone.OVERTIME
        if now >= self.soft_start_at:
            return TimeZone.CLOSING
        return TimeZone.NORMAL

    def elapsed_s(self, now: datetime) -> int:
        return max(int((now - self.started_at).total_seconds()), 0)

    def remaining_to_hard_s(self, now: datetime) -> int:
        return max(int((self.hard_end_at - now).total_seconds()), 0)

    def fits_before_hard_end(self, now: datetime, needed_s: int, reserve_s: int = 0) -> bool:
        return self.remaining_to_hard_s(now) - reserve_s >= needed_s
