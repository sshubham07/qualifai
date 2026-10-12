"""Postgres checkpointer for the interview graph (ADR-0003, spec-001 T-25).

LangGraph saves the state after every node into its own `checkpoint*` tables, in the same
database as everything else (ADR-0005). It speaks psycopg, so it gets a small pool of its own
next to SQLAlchemy's asyncpg one."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool


def conninfo(database_url: str) -> str:
    """SQLAlchemy URL (postgresql+asyncpg://…) → the plain libpq URL psycopg expects."""
    scheme, rest = database_url.split("://", 1)
    return f"{scheme.split('+')[0]}://{rest}"


@asynccontextmanager
async def open_checkpointer(
    database_url: str, max_size: int = 4
) -> AsyncIterator[AsyncPostgresSaver]:
    async with AsyncConnectionPool(
        conninfo(database_url),
        max_size=max_size,
        open=False,
        # What the saver asks of its connections; autocommit also lets setup() build indexes.
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
    ) as pool:
        saver = AsyncPostgresSaver(pool)  # type: ignore[arg-type]
        await saver.setup()  # creates / migrates the checkpoint tables; safe to repeat
        yield saver
