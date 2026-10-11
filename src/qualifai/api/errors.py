"""Domain errors → HTTP responses."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from qualifai.domain.errors import InterviewStateError, LLMOutputError


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(InterviewStateError)
    async def _state(_: Request, exc: InterviewStateError) -> JSONResponse:
        return JSONResponse(
            status_code=409, content={"error": "invalid_state", "message": str(exc)}
        )

    @app.exception_handler(LLMOutputError)
    async def _llm(_: Request, exc: LLMOutputError) -> JSONResponse:
        return JSONResponse(
            status_code=503, content={"error": "model_unavailable", "message": str(exc)}
        )
