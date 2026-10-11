import pytest
from hypothesis import given
from hypothesis import strategies as st

from qualifai.content.loader import tier_preset
from qualifai.domain.enums import CompanyTier, Confidence, HiringBand, ReadinessLabel
from qualifai.eval.aggregation import SkillScore
from qualifai.eval.verdict import BAND_ORDER, JDWeight, VerdictInput, band_for, compute_verdict

pytestmark = pytest.mark.unit


def skills(**scores: float) -> dict[str, SkillScore]:
    return {k: SkillScore(k, v, Confidence.HIGH, ("t",), 3) for k, v in scores.items()}


JD = {
    "kubernetes": JDWeight(3, True),
    "postgresql": JDWeight(3, True),
    "fastapi": JDWeight(2, False),
    "coding": JDWeight(2, False),
    "behavioral": JDWeight(1, False),
}
EXAMPLE = skills(kubernetes=8.1, postgresql=4.6, fastapi=7.5, coding=6.0, behavioral=7.0)


def vin(tier: CompanyTier, **kw) -> VerdictInput:
    t = tier_preset(tier)
    base = {
        "skills": EXAMPLE,
        "jd": JD,
        "must_coverage": 1.0,
        "bands": t.bands,
        "must_have_floor": t.must_have_floor,
    }
    base.update(kw)
    return VerdictInput(**base)


def test_ac5_service_tier_must_have_gate_caps_hire_to_lean_hire():
    r = compute_verdict(vin(CompanyTier.SERVICE))
    assert r.overall == 6.55
    assert band_for(6.55, tier_preset(CompanyTier.SERVICE).bands) is HiringBand.HIRE
    assert r.band is HiringBand.LEAN_HIRE
    assert r.label is ReadinessLabel.ALMOST_READY
    assert r.gates_applied == ("must_have_gate:postgresql",)


def test_same_performance_product_tier_is_lean_hire_without_gate_effect():
    r = compute_verdict(vin(CompanyTier.PRODUCT))
    assert r.band is HiringBand.LEAN_HIRE and r.gates_applied == ()


def test_maang_tier_is_stricter():
    assert compute_verdict(vin(CompanyTier.MAANG)).band is HiringBand.LEAN_NO_HIRE


def test_coverage_gate_withholds_verdict():
    r = compute_verdict(vin(CompanyTier.PRODUCT, must_coverage=0.5))
    assert r.band is HiringBand.INSUFFICIENT_EVIDENCE and r.overall is None
    assert r.label is ReadinessLabel.INCOMPLETE


def test_claim_and_coding_gates():
    strong = skills(kubernetes=9.5, postgresql=9.0, fastapi=9.0, coding=9.0, behavioral=9.0)
    assert compute_verdict(vin(CompanyTier.SERVICE, skills=strong)).band is HiringBand.STRONG_HIRE
    r = compute_verdict(vin(CompanyTier.SERVICE, skills=strong, contradicted_claims=1))
    assert r.band is HiringBand.LEAN_HIRE and "claim_gate" in r.gates_applied
    r = compute_verdict(vin(CompanyTier.SERVICE, skills=strong, coding_tests_ratio=0.3))
    assert r.band is HiringBand.HIRE and "coding_gate" in r.gates_applied


def test_integrity_flags_are_warnings_not_verdict_changes():
    r = compute_verdict(vin(CompanyTier.PRODUCT, integrity_flags=("3 large pastes",)))
    assert r.band is HiringBand.LEAN_HIRE and r.warnings == ("integrity: 3 large pastes",)


@given(st.floats(0, 10), st.floats(0, 10), st.integers(0, 2), st.sampled_from(list(CompanyTier)))
def test_gates_never_raise_the_band(k, p, contradicted, tier):
    s = skills(kubernetes=k, postgresql=p)
    jd = {"kubernetes": JDWeight(3, True), "postgresql": JDWeight(3, True)}
    t = tier_preset(tier)
    gated = compute_verdict(VerdictInput(s, jd, 1.0, t.bands, t.must_have_floor, contradicted))
    raw = band_for(gated.overall or 0, t.bands)
    assert BAND_ORDER.index(gated.band) <= BAND_ORDER.index(raw)
