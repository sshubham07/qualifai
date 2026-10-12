"""Domain errors → HTTP responses."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from qualifai.domain.errors import (
    InterviewNotFound,
    InterviewStateError,
    LLMOutputError,
    NotInterviewOwner,
    SpeechUnavailable,
)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(InterviewStateError)
    async def _state(_: Request, exc: InterviewStateError) -> JSONResponse:
        return JSONResponse(
            status_code=409, content={"error": "invalid_state", "message": str(exc)}
        )

    @app.exception_handler(InterviewNotFound)
    async def _missing(_: Request, exc: InterviewNotFound) -> JSONResponse:
        return JSONResponse(
            status_code=404, content={"error": "not_found", "message": "Interview not found"}
        )

    @app.exception_handler(NotInterviewOwner)
    async def _owner(_: Request, exc: NotInterviewOwner) -> JSONResponse:
        return JSONResponse(status_code=403, content={"error": "forbidden", "message": str(exc)})

    @app.exception_handler(LLMOutputError)
    async def _llm(_: Request, exc: LLMOutputError) -> JSONResponse:
        return JSONResponse(
            status_code=503, content={"error": "model_unavailable", "message": str(exc)}
        )

    @app.exception_handler(SpeechUnavailable)
    async def _speech(_: Request, exc: SpeechUnavailable) -> JSONResponse:
        return JSONResponse(
            status_code=503, content={"error": "speech_unavailable", "message": str(exc)}
        )
