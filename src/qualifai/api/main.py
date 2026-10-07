"""FastAPI application factory."""

from fastapi import FastAPI

from qualifai import __version__
from qualifai.api.errors import register_error_handlers
from qualifai.api.routes import health, interviews


def create_app() -> FastAPI:
    app = FastAPI(title="QualifAI", version=__version__)
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(interviews.router, prefix="/v1")
    return app


app = create_app()
