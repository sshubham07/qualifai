"""Verdict — computed by code from scores, never decided by the LLM (ADR-0008).

overall = Σ(skill_score × JD weight) / Σ(JD weight)  over ASSESSED skills only
then gates (which can only lower or withhold a verdict), then tier thresholds → band.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from qualifai.domain.enums import HiringBand, ReadinessLabel
from qualifai.eval.aggregation import SkillScore

BAND_ORDER = [
    HiringBand.NO_HIRE,
    HiringBand.LEAN_NO_HIRE,
    HiringBand.LEAN_HIRE,
    HiringBand.HIRE,
    HiringBand.STRONG_HIRE,
]
LABELS = {
    HiringBand.STRONG_HIRE: ReadinessLabel.READY,
    HiringBand.HIRE: ReadinessLabel.READY,
    HiringBand.LEAN_HIRE: ReadinessLabel.ALMOST_READY,
    HiringBand.LEAN_NO_HIRE: ReadinessLabel.NEEDS_PREPARATION,
    HiringBand.NO_HIRE: ReadinessLabel.NEEDS_PREPARATION,
    HiringBand.INSUFFICIENT_EVIDENCE: ReadinessLabel.INCOMPLETE,
}
MIN_MUST_COVERAGE = 0.75


@dataclass(frozen=True, slots=True)
class JDWeight:
    weight: int
    must_have: bool


@dataclass(frozen=True, slots=True)
class VerdictInput:
    skills: Mapping[str, SkillScore]
    jd: Mapping[str, JDWeight]
    must_coverage: float  # share of must-cover topics opened
    bands: Mapping[str, float]  # from tier preset: strong_hire, hire, lean_hire, lean_no_hire
    must_have_floor: float = 5.0
    contradicted_claims: int = 0
    coding_tests_ratio: float | None = None  # hidden tests passed / total, if a coding round ran
    integrity_flags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class VerdictResult:
    overall: float | None
    band: HiringBand
    label: ReadinessLabel
    gates_applied: tuple[str, ...] = ()
    warnings: tuple[str, ...] = field(default_factory=tuple)


def band_for(score: float, bands: Mapping[str, float]) -> HiringBand:
    for band in (
        HiringBand.STRONG_HIRE,
        HiringBand.HIRE,
        HiringBand.LEAN_HIRE,
        HiringBand.LEAN_NO_HIRE,
    ):
        if score >= bands[band.value]:
            return band
    return HiringBand.NO_HIRE


def _cap(band: HiringBand, ceiling: HiringBand) -> HiringBand:
    return min(band, ceiling, key=BAND_ORDER.index)


def compute_verdict(v: VerdictInput) -> VerdictResult:
    warnings = tuple(f"integrity: {f}" for f in v.integrity_flags)

    if v.must_coverage < MIN_MUST_COVERAGE:
        return VerdictResult(
            None,
            HiringBand.INSUFFICIENT_EVIDENCE,
            LABELS[HiringBand.INSUFFICIENT_EVIDENCE],
            ("coverage_gate",),
            warnings,
        )

    assessed = {k: s for k, s in v.skills.items() if k in v.jd}
    if not assessed:
        return VerdictResult(
            None,
            HiringBand.INSUFFICIENT_EVIDENCE,
            LABELS[HiringBand.INSUFFICIENT_EVIDENCE],
            ("no_assessed_skills",),
            warnings,
        )

    total_w = sum(v.jd[k].weight for k in assessed)
    overall = round(sum(s.score * v.jd[k].weight for k, s in assessed.items()) / total_w, 2)
    band = band_for(overall, v.bands)
    gates: list[str] = []

    weak_must = [
        k for k, s in assessed.items() if v.jd[k].must_have and s.score < v.must_have_floor
    ]
    if weak_must:
        capped = _cap(band, HiringBand.LEAN_HIRE)
        if capped != band:
            gates.append(f"must_have_gate:{','.join(sorted(weak_must))}")
        band = capped
    if v.contradicted_claims > 0:
        capped = _cap(band, HiringBand.LEAN_HIRE)
        if capped != band:
            gates.append("claim_gate")
        band = capped
    if v.coding_tests_ratio is not None and v.coding_tests_ratio < 0.5:
        capped = _cap(band, HiringBand.HIRE)
        if capped != band:
            gates.append("coding_gate")
        band = capped

    return VerdictResult(overall, band, LABELS[band], tuple(gates), warnings)
