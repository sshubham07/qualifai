from datetime import timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st

from qualifai.domain.enums import TimeZone
from qualifai.interview.time_window import MAX_LATENCY_CREDIT_S, TimeWindow

pytestmark = pytest.mark.unit


def test_45_minute_window_is_40_45_50(t0):
    w = TimeWindow.for_duration(t0, 45)
    assert w.soft_start_at - t0 == timedelta(minutes=40)
    assert w.target_end_at - t0 == timedelta(minutes=45)
    assert w.hard_end_at - t0 == timedelta(minutes=50)


@pytest.mark.parametrize(
    ("minute", "zone"),
    [
        (0, TimeZone.NORMAL),
        (39, TimeZone.NORMAL),
        (40, TimeZone.CLOSING),
        (44, TimeZone.CLOSING),
        (45, TimeZone.OVERTIME),
        (49, TimeZone.OVERTIME),
        (50, TimeZone.EXPIRED),
        (70, TimeZone.EXPIRED),
    ],
)
def test_zones(t0, minute, zone):
    assert TimeWindow.for_duration(t0, 45).zone(t0 + timedelta(minutes=minute)) is zone


def test_latency_credit_shifts_window_and_is_capped(t0):
    w = TimeWindow.for_duration(t0, 45)
    shifted = w.with_latency_credit(62)  # 2 s threshold → 60 s credit
    assert shifted.hard_end_at - w.hard_end_at == timedelta(seconds=60)
    capped = w.with_latency_credit(10_000)
    assert capped.hard_end_at - w.hard_end_at == timedelta(seconds=MAX_LATENCY_CREDIT_S)


def test_latency_credit_is_idempotent(t0):
    w = TimeWindow.for_duration(t0, 45).with_latency_credit(100)
    assert w.with_latency_credit(100) == w


def test_fits_before_hard_end(t0):
    w = TimeWindow.for_duration(t0, 45)
    now = t0 + timedelta(minutes=44)
    assert w.fits_before_hard_end(now, needed_s=180, reserve_s=120)
    assert not w.fits_before_hard_end(now, needed_s=300, reserve_s=120)


@given(st.integers(min_value=20, max_value=90))
def test_markers_always_ordered(target):
    from datetime import UTC, datetime

    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    w = TimeWindow.for_duration(t0, target)
    assert t0 < w.soft_start_at < w.target_end_at < w.hard_end_at
