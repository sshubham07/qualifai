"""FakeLLM responders for the Phase 1 tasks, shared by unit and integration tests."""

from pathlib import Path
from typing import Any

from qualifai.domain.enums import CompanyTier
from qualifai.domain.models import InterviewRequest
from qualifai.llm.fake import FakeLLM
from qualifai.llm.tasks import LLMTask

FIXTURES = Path(__file__).parent / "fixtures"
RESUME = (FIXTURES / "sample_resume.txt").read_text()
JD = (FIXTURES / "sample_jd.txt").read_text()


def request(**kw: Any) -> InterviewRequest:
    base: dict[str, Any] = {
        "resume_text": RESUME,
        "jd_text": JD,
        "round_type": "r1_technical",
        "company_tier": CompanyTier.PRODUCT,
        "experience_min_years": 3,
        "experience_max_years": 5,
    }
    return InterviewRequest(**{**base, **kw})


def intake(role: str = "backend_sde") -> dict[str, Any]:
    return {
        "role_family": role,
        "confidence": 0.9,
        "resume_role_family": "backend_sde",
        "is_resume": True,
        "is_jd": True,
    }


def prep_llm(
    role: str = "backend_sde", jd_skills: tuple[str, ...] = ("PostgreSQL", "k8s")
) -> FakeLLM:
    return FakeLLM(
        {
            LLMTask.INTAKE_GATE: lambda _s, _u: intake(role),
            LLMTask.RESUME_EXTRACT: lambda _s, _u: {
                "claims": [
                    {
                        "id": "c1",
                        "text": "Designed microservices using Kubernetes",
                        "skills": ["Kubernetes"],
                        "ownership_verb": "designed",
                        "evidence_level": "deep_ownership",
                    }
                ],
                "years_experience": 3.5,
            },
            LLMTask.JD_EXTRACT: lambda _s, _u: {
                "skills": [{"name": s, "weight": 3, "must_have": True} for s in jd_skills]
            },
            LLMTask.TOPIC_PACK: lambda _s, _u: {
                "opening_questions": ["Walk me through it."],
                "rubric": {"expected_points": ["trade-offs"]},
            },
        }
    )
