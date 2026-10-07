"""Interview endpoints. Thin: validate → call application service → map result.

POST /v1/interviews               submit resume + JD + round + tier  → 202 (prep enqueued)
GET  /v1/interviews/{id}          status, prep progress, server time
GET  /v1/interviews/{id}/events   SSE: prep progress, streamed questions
POST /v1/interviews/{id}/start    READY → IN_PROGRESS, returns first question
POST /v1/interviews/{id}/answers  submit answer, returns next question
GET  /v1/interviews/{id}/report   report JSON (HTML via ?format=html)
"""

from uuid import UUID

from fastapi import APIRouter, File, Form, UploadFile, status

from qualifai.api.schemas import AnswerIn, InterviewAccepted, InterviewStatusOut, NextQuestionOut
from qualifai.domain.enums import CompanyTier, RoundType

router = APIRouter(prefix="/interviews", tags=["interviews"])


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=InterviewAccepted)
async def create_interview(
    resume: UploadFile = File(...),
    jd_text: str = Form(...),
    round_type: RoundType = Form(...),
    company_tier: CompanyTier = Form(...),
    experience_min_years: int = Form(...),
    experience_max_years: int = Form(...),
    target_minutes: int = Form(45),
    company_name: str | None = Form(None),
) -> InterviewAccepted:
    # TODO(spec-001 T-20): PDF→text (pymupdf), run_intake() synchronously, dedupe by input hash,
    # persist interview SUBMITTED→PREPARING, upload PDF to object storage, enqueue prepare job.
    raise NotImplementedError


@router.get("/{interview_id}", response_model=InterviewStatusOut)
async def get_interview(interview_id: UUID) -> InterviewStatusOut:
    raise NotImplementedError  # TODO(spec-001 T-21)


@router.post("/{interview_id}/start", response_model=NextQuestionOut)
async def start_interview(interview_id: UUID) -> NextQuestionOut:
    # TODO(spec-001 T-22): check owner + READY + not expired; set TimeWindow; schedule hard-stop
    # job at hard_end + grace; InterviewService.start(); return first question.
    raise NotImplementedError


@router.post("/{interview_id}/answers", response_model=NextQuestionOut)
async def submit_answer(interview_id: UUID, body: AnswerIn) -> NextQuestionOut:
    # TODO(spec-001 T-23): record integrity events (paste, timing), compute answer_seconds,
    # InterviewService.submit_answer(); if ended → enqueue evaluation job.
    raise NotImplementedError


@router.get("/{interview_id}/report")
async def get_report(interview_id: UUID, format: str = "json") -> dict[str, object]:
    raise NotImplementedError  # TODO(spec-001 T-30)
