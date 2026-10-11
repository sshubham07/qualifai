"""Phase 1 intake: the four inputs (resume text, JD text, experience range, company type),
their validation, and the gate's decision: both documents must be for a software role."""

from functools import partial
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from openai import BadRequestError
from pydantic import ValidationError
from tenacity import wait_none
from tests.conftest import T0
from tests.prep_fakes import JD, RESUME, intake, request

from qualifai.api.deps import get_submit
from qualifai.api.main import create_app
from qualifai.api.schemas import InterviewIn
from qualifai.domain.clock import FrozenClock
from qualifai.domain.enums import CompanyTier, FailureCode, RoundType, SupportLevel
from qualifai.domain.errors import LLMOutputError
from qualifai.domain.failures import FAILURE_REASONS
from qualifai.domain.models import IntakeResult
from qualifai.llm import gateway
from qualifai.llm.gateway import LLMGateway
from qualifai.llm.router import ModelRoute, ModelRouter
from qualifai.llm.tasks import LLMTask
from qualifai.prep.intake_gate import decide
from qualifai.prep.submission import input_hash, submit_interview

pytestmark = pytest.mark.unit
NO_FRONTEND = Path("/nonexistent")


def test_company_types_are_service_startup_product_maang():
    assert {t.value for t in CompanyTier} == {"service", "startup", "product", "maang"}


@pytest.mark.parametrize(("lo", "hi", "ok"), [(3, 5, True), (4, 4, True), (6, 5, False)])
def test_experience_range_must_be_ordered(lo, hi, ok):
    if ok:
        assert request(experience_min_years=lo, experience_max_years=hi)
    else:
        with pytest.raises(ValidationError):
            request(experience_min_years=lo, experience_max_years=hi)


def test_input_hash_is_stable_and_sensitive_to_every_input():
    base = input_hash(request())
    assert input_hash(request()) == base
    assert input_hash(request(company_tier=CompanyTier.MAANG)) != base
    assert input_hash(request(experience_max_years=6)) != base
    assert input_hash(request(resume_text=RESUME + " ")) != base


def test_interview_in_defaults_to_r1_and_normalises_email():
    body = InterviewIn(
        email="  Dev@Example.COM ",
        resume_text=RESUME,
        jd_text=JD,
        company_tier="startup",
        experience_min_years=3,
        experience_max_years=5,
    )
    assert body.email == "dev@example.com"
    assert body.to_request() == request(company_tier=CompanyTier.STARTUP)
    assert body.to_request().round_type is RoundType.R1_TECHNICAL


def test_interview_in_needs_no_email():
    body = InterviewIn(
        resume_text=RESUME,
        jd_text=JD,
        company_tier="startup",
        experience_min_years=3,
        experience_max_years=5,
    )
    assert body.email is None
    assert body.to_request() == request(company_tier=CompanyTier.STARTUP)


@pytest.mark.parametrize(
    ("patch", "expected"),
    [
        ({}, SupportLevel.FULL),
        ({"jd_role_family": "fullstack"}, SupportLevel.PARTIAL),
        ({"resume_role_family": "frontend"}, SupportLevel.FULL),  # support follows the JD
        ({"jd_role_family": "non_technical"}, FailureCode.JD_NOT_SOFTWARE),  # AC-1: an MBA JD
        ({"resume_role_family": "non_technical"}, FailureCode.RESUME_NOT_SOFTWARE),
        ({"is_resume": False}, FailureCode.NOT_A_RESUME),
        ({"is_jd": False}, FailureCode.NOT_A_JD),
        ({"confidence": 0.3}, FailureCode.UNDECIDED),
        ({"jd_role_family": "unknown"}, FailureCode.UNDECIDED),
        ({"resume_role_family": "unknown"}, FailureCode.UNDECIDED),
        (
            {"resume_role_family": "non_technical", "confidence": 0.1},
            FailureCode.RESUME_NOT_SOFTWARE,
        ),
    ],
)
def test_ac1_gate_needs_a_software_resume_and_a_software_jd(patch, expected):
    assert decide(IntakeResult(**intake(**patch))) is expected


def test_every_failure_code_has_a_reason_to_show():
    assert set(FAILURE_REASONS) == set(FailureCode) and all(FAILURE_REASONS.values())


class UntouchableSession:
    def __getattr__(self, name: str) -> object:
        raise AssertionError(f"session.{name} used for a request that failed validation")


def client(enqueued: list) -> TestClient:
    async def enqueue(interview_id):
        enqueued.append(interview_id)

    app = create_app(NO_FRONTEND)
    app.dependency_overrides[get_submit] = lambda: partial(
        submit_interview, UntouchableSession(), enqueue, FrozenClock(T0)
    )
    return TestClient(app)  # no `with`: lifespan (Redis pool) is not started


def body(**kw) -> dict:
    base = {
        "email": "dev@example.com",
        "resume_text": RESUME,
        "jd_text": JD,
        "company_tier": "product",
        "experience_min_years": 3,
        "experience_max_years": 5,
    }
    return {**base, **kw}


@pytest.mark.parametrize(
    "patch",
    [
        {"experience_min_years": 8, "experience_max_years": 3},
        {"company_tier": "faang"},  # renamed to maang
        {"resume_text": "too short"},
        {"jd_text": "too short"},
        {"email": "not-an-email"},
    ],
)
def test_invalid_inputs_are_rejected_before_anything_is_stored_or_enqueued(patch):
    enqueued: list = []
    resp = client(enqueued).post("/v1/interviews", json=body(**patch))
    assert resp.status_code == 422
    assert enqueued == []


class _Msg:
    def __init__(self, content: str) -> None:
        self.message = type("M", (), {"content": content})()


class _FlakyClient:
    """Returns invalid JSON `bad` times, then a valid IntakeResult."""

    def __init__(self, bad: int, error: Exception | None = None) -> None:
        self.calls, self._bad, self._error = 0, bad, error
        self.chat = type("Chat", (), {"completions": self})()

    async def create(self, **_: object) -> object:
        self.calls += 1
        if self.calls <= self._bad and self._error is not None:
            raise self._error
        content = "{}" if self.calls <= self._bad else IntakeResult(**intake()).model_dump_json()
        return type("Resp", (), {"choices": [_Msg(content)], "usage": None})()


def _gateway(fake: _FlakyClient) -> LLMGateway:
    route = ModelRoute(provider="p", model="m")
    return LLMGateway(ModelRouter(dict.fromkeys(LLMTask, route)), {"p": fake})  # type: ignore[dict-item]


async def test_gateway_retries_invalid_output_then_succeeds(monkeypatch):
    monkeypatch.setattr(gateway, "_RETRY_WAIT", wait_none())
    fake = _FlakyClient(bad=2)
    out = await _gateway(fake).structured(LLMTask.INTAKE_GATE, "s", "u", IntakeResult)
    assert out.is_resume and fake.calls == 3


async def test_gateway_gives_up_after_three_attempts(monkeypatch):
    monkeypatch.setattr(gateway, "_RETRY_WAIT", wait_none())
    fake = _FlakyClient(bad=5)
    with pytest.raises((ValidationError, LLMOutputError)):
        await _gateway(fake).structured(LLMTask.INTAKE_GATE, "s", "u", IntakeResult)
    assert fake.calls == 3


def _bad_request(code: str) -> BadRequestError:
    response = httpx.Response(400, request=httpx.Request("POST", "http://provider"))
    return BadRequestError("rejected", response=response, body={"code": code})


async def test_gateway_retries_json_the_provider_rejected(monkeypatch):
    # e.g. a reasoning model that spent max_tokens before finishing the document
    monkeypatch.setattr(gateway, "_RETRY_WAIT", wait_none())
    fake = _FlakyClient(bad=1, error=_bad_request("json_validate_failed"))
    out = await _gateway(fake).structured(LLMTask.INTAKE_GATE, "s", "u", IntakeResult)
    assert out.is_resume and fake.calls == 2


async def test_gateway_does_not_retry_other_bad_requests(monkeypatch):
    monkeypatch.setattr(gateway, "_RETRY_WAIT", wait_none())
    fake = _FlakyClient(bad=5, error=_bad_request("model_not_found"))
    with pytest.raises(BadRequestError):
        await _gateway(fake).structured(LLMTask.INTAKE_GATE, "s", "u", IntakeResult)
    assert fake.calls == 1


def test_api_serves_the_built_web_app_without_shadowing_api_routes(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("js")
    (tmp_path / "index.html").write_text("<html>spa</html>")
    (tmp_path / "favicon.svg").write_text("<svg/>")
    http = TestClient(create_app(tmp_path))

    for page in ("/", "/start", "/interviews/abc"):  # client-side routes all get the shell
        assert http.get(page).text == "<html>spa</html>"
    assert http.get("/assets/app.js").text == "js"
    assert http.get("/favicon.svg").text == "<svg/>"
    assert http.get("/healthz").json() == {"status": "ok"}
    assert http.get("/v1/nope").status_code == 404
    assert http.get("/..%2F..%2Fpyproject.toml").text == "<html>spa</html>"  # no path escape


def test_api_runs_without_a_frontend_build():
    http = TestClient(create_app(NO_FRONTEND))
    assert http.get("/healthz").status_code == 200 and http.get("/").status_code == 404
