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
# Names nothing the sample JD asks for: the match check reads the resume text as well as the claims.
FRONTEND_RESUME = (
    "Frontend Engineer, 4 years. Built a design system in React and TypeScript used by twelve "
    "product teams; led the migration from Redux to React Query; raised the Lighthouse score from "
    "62 to 94 with code splitting; wrote Storybook docs and Jest tests; built accessible forms."
)


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


def intake(**kw: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "is_resume": True,
        "is_jd": True,
        "resume_role_family": "backend_sde",
        "jd_role_family": "backend_sde",
        "confidence": 0.9,
    }
    return {**base, **kw}


OPENING = "Walk me through the Kubernetes platform you designed and your part in it."


def prep_llm(
    jd_skills: tuple[str, ...] = ("PostgreSQL", "k8s"),
    resume_skills: tuple[str, ...] = ("Kubernetes",),
    **intake_kw: Any,
) -> FakeLLM:
    return FakeLLM(
        {
            LLMTask.INTAKE_GATE: lambda _s, _u: intake(**intake_kw),
            LLMTask.RESUME_EXTRACT: lambda _s, _u: {
                "claims": [
                    {
                        "id": "c1",
                        "text": "Designed microservices using Kubernetes",
                        "skills": list(resume_skills),
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
            LLMTask.OPENING_QUESTION: lambda _s, _u: {"question": OPENING},
        }
    )
