from datetime import UTC, datetime

import pytest

from qualifai.domain.enums import AnswerIntent, ClaimConsistency, Specificity, TimeZone
from qualifai.domain.models import TurnSignals
from qualifai.interview.policy import PolicyInput

T0 = datetime(2026, 10, 7, 10, 0, tzinfo=UTC)


@pytest.fixture
def t0() -> datetime:
    return T0


def signals(**kw: object) -> TurnSignals:
    base: dict[str, object] = {
        "intent": AnswerIntent.ANSWER,
        "coverage_ratio": 0.5,
        "specificity": Specificity.MEDIUM,
        "consistency": ClaimConsistency.CONSISTENT,
    }
    base.update(kw)
    return TurnSignals(**base)  # type: ignore[arg-type]


def policy_input(**kw: object) -> PolicyInput:
    base: dict[str, object] = {
        "zone": TimeZone.NORMAL,
        "remaining_to_hard_s": 30 * 60,
        "signals": signals(),
        "topic_is_must": True,
        "topic_budget_s": 300,
        "topic_used_s": 60,
        "depth": 0,
        "max_depth": 3,
        "scaffold_used": False,
        "unvisited_must_min_s": (180,),
        "next_topic_estimate_s": 300,
    }
    base.update(kw)
    return PolicyInput(**base)  # type: ignore[arg-type]


# ---- real Postgres / Redis via testcontainers (integration + HTTP e2e); skipped without Docker
@pytest.fixture(scope="session")
def pg_url():
    containers = pytest.importorskip("testcontainers.postgres")
    try:
        with containers.PostgresContainer("pgvector/pgvector:pg16", driver="asyncpg") as pg:
            yield pg.get_connection_url()
    except Exception as exc:  # Docker not available
        pytest.skip(f"Docker unavailable: {exc}")


@pytest.fixture(scope="session")
def redis_url():
    containers = pytest.importorskip("testcontainers.redis")
    try:
        with containers.RedisContainer("redis:7-alpine") as redis:
            host, port = redis.get_container_host_ip(), redis.get_exposed_port(6379)
            yield f"redis://{host}:{port}/0"
    except Exception as exc:  # Docker not available
        pytest.skip(f"Docker unavailable: {exc}")
