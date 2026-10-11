"""Phase 1 intake: the four inputs (resume text, JD text, experience range, company type),
their validation, and the gate running before anything is stored or enqueued."""

from functools import partial
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from tenacity import wait_none
from tests.conftest import T0
from tests.prep_fakes import JD, RESUME, intake, prep_llm, request

from qualifai.api.deps import get_submit
from qualifai.api.main import create_app
from qualifai.api.schemas import InterviewIn
from qualifai.domain.clock import FrozenClock
from qualifai.domain.enums import CompanyTier, RoundType
from qualifai.domain.errors import LLMOutputError
from qualifai.domain.models import IntakeResult
from qualifai.llm import gateway
from qualifai.llm.gateway import LLMGateway
from qualifai.llm.router import ModelRoute, ModelRouter
from qualifai.llm.tasks import LLMTask
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


class UntouchableSession:
    def __getattr__(self, name: str) -> object:
        raise AssertionError(f"session.{name} used before the intake gate passed")


def client(llm, enqueued: list) -> TestClient:
    async def enqueue(interview_id):
        enqueued.append(interview_id)

    app = create_app(NO_FRONTEND)
    app.dependency_overrides[get_submit] = lambda: partial(
        submit_interview, UntouchableSession(), llm, enqueue, FrozenClock(T0)
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


def test_ac1_unsupported_role_gets_422_and_nothing_is_enqueued():
    enqueued: list = []
    resp = client(prep_llm(role="non_technical"), enqueued).post("/v1/interviews", json=body())
    assert resp.status_code == 422
    assert resp.json()["error"] == "unsupported_role"
    assert enqueued == []


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
def test_invalid_inputs_are_rejected_before_any_llm_call(patch):
    llm, enqueued = prep_llm(), []
    resp = client(llm, enqueued).post("/v1/interviews", json=body(**patch))
    assert resp.status_code == 422
    assert llm.calls == [] and enqueued == []


class _Msg:
    def __init__(self, content: str) -> None:
        self.message = type("M", (), {"content": content})()


class _FlakyClient:
    """Returns invalid JSON `bad` times, then a valid IntakeResult."""

    def __init__(self, bad: int) -> None:
        self.calls, self._bad = 0, bad
        self.chat = type("Chat", (), {"completions": self})()

    async def create(self, **_: object) -> object:
        self.calls += 1
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
