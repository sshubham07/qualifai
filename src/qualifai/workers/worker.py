"""arq worker settings: prep, evaluation, hard-stop and the daily expiry sweep."""

from contextlib import AsyncExitStack
from typing import Any, ClassVar

from arq import cron
from arq.connections import RedisSettings

from qualifai.config.settings import get_settings
from qualifai.container import get_llm, open_live_runtime
from qualifai.db.session import SessionFactory
from qualifai.workers.jobs.cleanup import expire_kits
from qualifai.workers.jobs.evaluate import evaluate_interview_job
from qualifai.workers.jobs.hard_stop import hard_stop_job
from qualifai.workers.jobs.prepare import prepare_interview_job


async def startup(ctx: dict[str, Any]) -> None:
    ctx["llm"] = get_llm()
    ctx["stack"] = stack = AsyncExitStack()
    # ctx["redis"] is arq's own pool; the hard-stop job reads drafts and publishes through it.
    ctx["live"] = await stack.enter_async_context(open_live_runtime(ctx["redis"], SessionFactory))


async def shutdown(ctx: dict[str, Any]) -> None:
    await ctx["stack"].aclose()


class WorkerSettings:
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    functions: ClassVar[list[Any]] = [prepare_interview_job, evaluate_interview_job, hard_stop_job]
    cron_jobs: ClassVar[list[Any]] = [cron(expire_kits, hour=3, minute=17)]  # daily, off-peak
    max_jobs = 4
    job_timeout = 20 * 60
