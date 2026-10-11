import pytest

from qualifai.content.loader import round_template, tier_preset
from qualifai.domain.enums import CompanyTier, EvidenceLevel, ProbeType, RoundType, TopicPriority
from qualifai.domain.models import JDSkill, ResumeClaim
from qualifai.prep.gap_matrix import build_gap_matrix
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
