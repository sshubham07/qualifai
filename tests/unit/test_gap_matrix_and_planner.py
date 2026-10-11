import pytest

from qualifai.content.loader import round_template, tier_preset
from qualifai.domain.enums import CompanyTier, EvidenceLevel, ProbeType, RoundType, TopicPriority
from qualifai.domain.models import JDSkill, ResumeClaim
from qualifai.prep.gap_matrix import build_gap_matrix, round_skills
from qualifai.prep.planner import PlanningConfig, allocate_phases, build_plan, start_difficulty

pytestmark = pytest.mark.unit

CLAIMS = [
    ResumeClaim(
        id="c1",
        text="Designed microservices using Kubernetes",
        skills=("kubernetes",),
        ownership_verb="designed",
        evidence_level=EvidenceLevel.DEEP_OWNERSHIP,
    ),
    ResumeClaim(
        id="c2",
        text="Used PostgreSQL",
        skills=("postgresql",),
        ownership_verb="used",
        evidence_level=EvidenceLevel.MENTIONED,
    ),
]
JD = [
    JDSkill(name="kubernetes", weight=3, must_have=True),
    JDSkill(name="postgresql", weight=3, must_have=True),
    JDSkill(name="caching", weight=1, must_have=False),
]


def test_gap_matrix_probe_types():
    rows = {r.skill: r for r in build_gap_matrix(JD, CLAIMS)}
    assert rows["kubernetes"].probe_type is ProbeType.VERIFY_CLAIM
    assert rows["kubernetes"].claim_id == "c1"
    assert (
        rows["postgresql"].probe_type is ProbeType.TEST_GAP
    )  # JD needs it, resume barely shows it
    assert rows["caching"].probe_type is ProbeType.LIGHT


def test_gap_matrix_sorted_by_priority():
    rows = build_gap_matrix(JD, CLAIMS)
    assert rows[0].skill == "kubernetes"
    assert rows[-1].skill == "caching"


FOCUSED = [RoundType.DSA, RoundType.R2_LLD, RoundType.R3_HLD, RoundType.R4_MANAGERIAL]


@pytest.mark.parametrize("round_type", FOCUSED)
def test_a_focused_round_plans_its_own_skills(round_type):
    template = round_template(round_type)
    rows = build_gap_matrix(round_skills(template.skills), CLAIMS)
    plan = build_plan(rows, template, tier_preset(CompanyTier.PRODUCT), 45, "core")
    assert {s for t in plan.topics for s in t.skills} == set(template.skills)
    musts = {s for t in plan.topics if t.priority is TopicPriority.MUST for s in t.skills}
    assert {s for s, w in template.skills.items() if w == 3} <= musts  # weight 3 is always asked
    assert all(1 <= w <= 3 for w in template.skills.values())


def test_the_general_round_takes_its_topics_from_the_jd():
    assert round_template(RoundType.R1_TECHNICAL).skills == {}


def test_a_round_skill_the_resume_shows_is_verified_against_the_claim():
    claim = CLAIMS[0].model_copy(update={"skills": ("system_design",)})
    rows = {r.skill: r for r in build_gap_matrix(round_skills({"system_design": 3}), [claim])}
    assert rows["system_design"].probe_type is ProbeType.VERIFY_CLAIM
    assert rows["system_design"].claim_id == "c1"


@pytest.mark.parametrize("round_type", list(RoundType))
@pytest.mark.parametrize("minutes", [30, 45, 60])
def test_phase_budgets_sum_to_duration(round_type, minutes):
    phases = allocate_phases(round_template(round_type), minutes)
    assert sum(p.seconds for p in phases) == minutes * 60
    assert any(p.reserved for p in phases)


def test_plan_priorities_and_budgets():
    plan = build_plan(
        build_gap_matrix(JD, CLAIMS),
        round_template(RoundType.R1_TECHNICAL),
        tier_preset(CompanyTier.PRODUCT),
        45,
        "core",
        PlanningConfig(must_count=2, should_count=1, bonus_count=0),
    )
    prios = [t.priority for t in plan.topics]
    assert prios == [TopicPriority.MUST, TopicPriority.MUST, TopicPriority.SHOULD]
    core = next(p.seconds for p in plan.phases if p.name == "core")
    assert sum(t.budget_seconds for t in plan.topics) <= core + 180 * len(plan.topics)
    assert all(t.max_depth == tier_preset(CompanyTier.PRODUCT).max_depth for t in plan.topics)


@pytest.mark.parametrize(
    ("tier", "years", "expected"),
    [(CompanyTier.SERVICE, 3, 1), (CompanyTier.PRODUCT, 5, 3), (CompanyTier.MAANG, 8, 4)],
)
def test_start_difficulty(tier, years, expected):
    assert start_difficulty(tier_preset(tier), years) == expected
