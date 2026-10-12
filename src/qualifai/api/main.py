"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from qualifai import __version__
from qualifai.api.errors import register_error_handlers
from qualifai.api.routes import health, interviews
from qualifai.config.settings import get_settings
from qualifai.container import open_live_runtime
from qualifai.db.session import SessionFactory


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.arq = await create_pool(RedisSettings.from_dsn(get_settings().redis_url))
    async with open_live_runtime(app.state.arq, SessionFactory) as app.state.live:
        yield
    await app.state.arq.aclose()


def mount_frontend(app: FastAPI, dist: Path) -> None:
    """Serve the built single-page app (ADR-0015). Without a build the API runs on its own."""
    if not (dist / "index.html").is_file():
        return
    root = dist.resolve()
    app.mount("/assets", StaticFiles(directory=root / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:  # sync: file checks run in the threadpool
        if path.startswith("v1/"):
            raise HTTPException(404)  # unknown API route, not a page
        file = (root / path).resolve()
        is_asset = root in file.parents and file.is_file()
        return FileResponse(file if is_asset else root / "index.html")


def create_app(frontend_dist: Path | None = None) -> FastAPI:
    app = FastAPI(title="QualifAI", version=__version__, lifespan=lifespan)
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(interviews.router, prefix="/v1")
    mount_frontend(app, frontend_dist or Path(get_settings().frontend_dist))  # last: catch-all
    return app


app = create_app()
