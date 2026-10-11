import pytest

testcontainers = pytest.importorskip("testcontainers.postgres")


@pytest.fixture(scope="session")
def pg_url():
    try:
        with testcontainers.PostgresContainer("pgvector/pgvector:pg16", driver="asyncpg") as pg:
            yield pg.get_connection_url()
    except Exception as exc:  # Docker not available
        pytest.skip(f"Docker unavailable: {exc}")
