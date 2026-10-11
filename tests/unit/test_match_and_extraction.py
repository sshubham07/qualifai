"""Resume ↔ JD match (spec-001 FR-18, AC-6) and the skill normalisation that feeds it."""

import asyncio

import pytest
from tests.prep_fakes import FRONTEND_RESUME, prep_llm, request

from qualifai.content.loader import round_template, skill_parents, tier_preset
from qualifai.domain.enums import CompanyTier, EvidenceLevel, FailureCode, ProbeType, RoundType
from qualifai.domain.errors import PrepRejected
from qualifai.domain.models import GapRow, ResumeClaim
from qualifai.llm.tasks import LLMTask
from qualifai.prep.extraction import extract_jd, extract_resume
from qualifai.prep.match import assess_match, decide_match, match_reason, mentions
from qualifai.prep.opening import write_opening_question
from qualifai.prep.pipeline import prepare_kit
from qualifai.prep.planner import build_plan
from qualifai.prep.topic_packs import PACK_CONCURRENCY, TopicPack, build_all_packs

pytestmark = pytest.mark.unit


def row(skill: str, weight: int, evidence: EvidenceLevel = EvidenceLevel.NONE) -> GapRow:
    return GapRow(
        skill=skill,
        jd_weight=weight,
        must_have=weight == 3,
        evidence=evidence,
        probe_type=ProbeType.TEST_GAP,
        priority_score=float(weight),
    )


SHOWN = EvidenceLevel.MENTIONED


@pytest.mark.parametrize(
    ("rows", "score", "verdict"),
    [
        ([row("python", 3, SHOWN), row("postgresql", 3, SHOWN)], 1.0, None),
        ([row("python", 3, SHOWN), row("postgresql", 3)], 0.5, None),
        # a partial fit goes ahead, however small: only "totally off" stops prep
        ([row("docker", 1, SHOWN), row("python", 3), row("postgresql", 3)], 0.143, None),
        ([row("python", 3), row("postgresql", 3)], 0.0, FailureCode.RESUME_JD_NO_MATCH),
        ([], 0.0, FailureCode.RESUME_JD_NO_MATCH),
    ],
)
def test_ac6_only_a_resume_showing_nothing_the_jd_asks_for_is_rejected(rows, score, verdict):
    report = assess_match(rows)
    assert report.score == score
    assert decide_match(report) is verdict


@pytest.mark.parametrize(
    ("text", "names", "found"),
    [
        ("developed django/drf rest apis for a fintech platform", ["api design", "api"], True),
        ("maintained jenkins ci/cd pipelines", ["ci/cd"], True),
        ("built with c++ and node.js", ["c++"], True),
        ("github actions workflows", ["git"], False),  # a whole word, not a prefix
        ("javascript on the client", ["java"], False),
        ("anything", [""], False),
    ],
)
def test_mentions_finds_whole_words_and_plurals(text, names, found):
    assert mentions(text, names) is found


def test_a_skill_the_resume_text_names_counts_even_if_no_claim_was_tagged_with_it():
    # Regression: "Django/DRF REST APIs" was tagged django only, so api_design counted as missing
    # and a Python backend resume was failed against a Python full-stack JD.
    rows = [row("python", 3, SHOWN), row("api_design", 3), row("ci/cd", 2), row("angular", 3)]
    resume = "Developed Django/DRF REST APIs. Maintained Jenkins CI/CD pipelines."
    tags_only = assess_match(rows)
    with_text = assess_match(rows, resume, {"rest api": "api_design", "api": "api_design"})
    assert tags_only.score == 0.273 and tags_only.missing == ("api_design", "ci/cd", "angular")
    assert with_text.matched == ("python", "api_design", "ci/cd") and with_text.score == 0.727
    assert with_text.missing == ("angular",) and decide_match(with_text) is None


def test_match_reason_names_the_skills_the_jd_asks_for():
    reason = match_reason(assess_match([*(row(s, 3) for s in "abcdefg"), row("api_design", 3)]))
    assert "(a, b, c, d, e and 3 more)" in reason
    assert "(api design)" in match_reason(assess_match([row("api_design", 3)]))  # ids as words


def test_taxonomy_parents():
    assert skill_parents()["fastapi"] == "python"
    assert "python" not in skill_parents()


async def test_resume_skills_are_normalised_show_their_parent_and_keep_unknown_ones():
    llm = prep_llm(resume_skills=("Fast API", "Postgres", " React ", "postgresql", ""))
    [claim] = (await extract_resume(llm, "resume")).claims
    assert claim.skills == ("fastapi", "python", "postgresql", "relational_db", "react")
    assert llm.calls[0][1] == "<resume>resume</resume>"  # the document travels as tagged data


async def test_jd_skills_split_into_taxonomy_and_other_keeping_the_heaviest():
    llm = prep_llm()
    llm._responders[LLMTask.JD_EXTRACT] = lambda _s, _u: {
        "skills": [
            {"name": "Postgres", "weight": 1, "must_have": False},
            {"name": "PostgreSQL", "weight": 3, "must_have": True},
            {"name": "React", "weight": 2, "must_have": True},
        ],
        "other_skills": [{"name": "invented", "weight": 3, "must_have": True}],  # never trusted
    }
    jd = await extract_jd(llm, "jd")
    assert [(s.name, s.weight) for s in jd.skills] == [("postgresql", 3)]
    assert [(s.name, s.weight) for s in jd.other_skills] == [("react", 2)]


async def _noop(_step: str) -> None:
    return None


async def test_a_skill_outside_the_taxonomy_still_counts_towards_the_match():
    # JD: React (unknown to us) + PostgreSQL; resume: React only. Without React the match would
    # be 0 and a fair interview would be refused.
    llm = prep_llm(jd_skills=("React", "PostgreSQL"), resume_skills=("react",))
    kit = await prepare_kit(llm, request(resume_text=FRONTEND_RESUME), _noop)
    assert kit.match.matched == ("react",) and kit.match.score == 0.5
    assert [g.skill for g in kit.gaps] == ["postgresql"]  # questions only on what we can assess


async def test_no_askable_skill_is_reported_before_the_match():
    with pytest.raises(PrepRejected) as stop:
        await prepare_kit(prep_llm(jd_skills=("COBOL",)), request(), _noop)
    assert stop.value.code is FailureCode.NO_KNOWN_SKILLS and stop.value.reason is None


async def test_opening_question_prompt_leads_with_planned_claims_and_carries_experience():
    def claim(i: int) -> ResumeClaim:
        return ResumeClaim(
            id=f"c{i}",
            text=f"claim {i}",
            skills=("kubernetes",) if i == 4 else (),
            ownership_verb="built",
            evidence_level=EvidenceLevel.PROJECT,
        )

    claims = [claim(i) for i in range(1, 5)]
    template, tier = round_template(RoundType.R1_TECHNICAL), tier_preset(CompanyTier.PRODUCT)
    plan = build_plan(
        [row("kubernetes", 3, EvidenceLevel.PROJECT).model_copy(update={"claim_id": "c4"})],
        template,
        tier,
        45,
        "core",
    )
    llm = prep_llm()
    out = await write_opening_question(llm, request(), template, tier, claims, plan.topics, 3.5)

    [(task, prompt)] = llm.calls
    assert task is LLMTask.OPENING_QUESTION and out.startswith("Walk me through")
    assert "- claim 4\n- claim 1\n- claim 2\n</resume_claims>" in prompt  # verified claim first
    assert "claim 3" not in prompt  # bounded: three claims, not the resume
    assert "3–5 years" in prompt and "3.5 years" in prompt and "cover: kubernetes" in prompt


async def test_a_focused_round_asks_its_own_topics_in_its_own_style():
    llm = prep_llm()
    kit = await prepare_kit(llm, request(round_type="r3_hld", target_minutes=60), _noop)
    hld = round_template(RoundType.R3_HLD)
    assert {s for t in kit.plan.topics for s in t.skills} == set(hld.skills)
    assert [g.skill for g in kit.gaps] == ["kubernetes", "postgresql"]  # the JD still gates the fit
    assert sum(p.seconds for p in kit.plan.phases) == 60 * 60
    packs = [prompt for task, prompt in llm.calls if task is LLMTask.TOPIC_PACK]
    assert len(packs) == len(hld.skills)
    assert all(hld.rules.strip() in p and "R3 High-Level Design" in p for p in packs)


class _SlowLLM:
    """Counts how many structured calls are in flight at once."""

    def __init__(self) -> None:
        self.active = self.peak = 0

    async def structured(self, task, system, user, schema):
        self.active += 1
        self.peak = max(self.peak, self.active)
        await asyncio.sleep(0)  # let the other packs start if nothing holds them back
        self.active -= 1
        return TopicPack.model_validate(
            {"opening_questions": [user[:0] + "q"], "rubric": {"expected_points": ["p"]}}
        )


async def test_topic_packs_are_written_a_few_at_a_time_in_plan_order():
    template, tier = round_template(RoundType.R1_TECHNICAL), tier_preset(CompanyTier.PRODUCT)
    plan = build_plan([row(f"s{i}", 3) for i in range(8)], template, tier, 45, "core")
    llm = _SlowLLM()
    packed = await build_all_packs(llm, list(plan.topics), template, tier, {})  # type: ignore[arg-type]
    assert llm.peak == PACK_CONCURRENCY
    assert [t.id for t in packed] == [t.id for t in plan.topics]
    assert all(t.opening_questions for t in packed)
