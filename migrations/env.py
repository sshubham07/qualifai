"""Alembic environment — async engine, metadata from qualifai.db.models."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from qualifai.config.settings import get_settings
from qualifai.db.models import Base

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_name(name: str | None, type_: str, parent_names: object) -> bool:
    """LangGraph's checkpointer creates and migrates its own tables (interview/checkpoint.py);
    autogenerate must not try to drop them."""
    return not (type_ == "table" and (name or "").startswith("checkpoint"))


def run_migrations_offline() -> None:
    context.configure(
        url=get_settings().database_url, target_metadata=target_metadata, include_name=include_name
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run(connection) -> None:  # type: ignore[no-untyped-def]
    context.configure(
        connection=connection, target_metadata=target_metadata, include_name=include_name
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(get_settings().database_url)
    async with engine.connect() as conn:
        await conn.run_sync(_do_run)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
