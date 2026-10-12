"""Gap matrix — deterministic. For every JD skill: how strong is the resume evidence, and
therefore what should the interview do with it?

    high JD weight + strong claim   → VERIFY_CLAIM  ("You designed X — walk me through it")
    high JD weight + weak/no claim  → TEST_GAP      (JD needs PostgreSQL, resume barely shows it)
    low JD weight                   → LIGHT

A verified claim is project talk, so the plan also asks about that skill on its own terms
(FUNDAMENTALS, ADR-0023).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from qualifai.domain.enums import EvidenceLevel, ProbeType
from qualifai.domain.models import GapRow, JDSkill, ResumeClaim

_EVIDENCE_RANK = {
    EvidenceLevel.NONE: 0,
    EvidenceLevel.MENTIONED: 1,
    EvidenceLevel.PROJECT: 2,
    EvidenceLevel.DEEP_OWNERSHIP: 3,
}
# How valuable is probing, per probe type (verifying a strong claim is the most informative).
_PROBE_FACTOR = {
    ProbeType.VERIFY_CLAIM: 1.2,
    ProbeType.TEST_GAP: 1.0,
    ProbeType.FUNDAMENTALS: 0.8,
    ProbeType.LIGHT: 0.4,
}


def _score(weight: int, must_have: bool, probe: ProbeType) -> float:
    return round(weight * _PROBE_FACTOR[probe] * (1.5 if must_have else 1.0), 3)


def strongest_claim(skill: str, claims: Sequence[ResumeClaim]) -> ResumeClaim | None:
    relevant = [c for c in claims if skill in c.skills]
    return max(relevant, key=lambda c: _EVIDENCE_RANK[c.evidence_level], default=None)


def round_skills(skills: Mapping[str, int]) -> list[JDSkill]:
    """A focused round asks about its own skills (content/rounds/*.yaml), not the JD's: they go
    through the same matrix, so a resume claim that shows one is still verified (ADR-0019)."""
    return [JDSkill(name=name, weight=w, must_have=w >= 3) for name, w in skills.items()]


def with_round_extras(jd_skills: Sequence[JDSkill], always: Mapping[str, int]) -> list[JDSkill]:
    """The JD's skills plus those the round asks about whatever the JD lists."""
    named = {s.name for s in jd_skills}
    extra = [
        JDSkill(name=n, weight=w, must_have=False) for n, w in always.items() if n not in named
    ]
    return [*jd_skills, *extra]


def build_gap_matrix(jd_skills: Sequence[JDSkill], claims: Sequence[ResumeClaim]) -> list[GapRow]:
    rows: list[GapRow] = []
    for s in jd_skills:
        claim = strongest_claim(s.name, claims)
        evidence = claim.evidence_level if claim else EvidenceLevel.NONE
        high_weight = s.must_have or s.weight >= 2
        if not high_weight:
            probe = ProbeType.LIGHT
        elif _EVIDENCE_RANK[evidence] >= _EVIDENCE_RANK[EvidenceLevel.PROJECT]:
            probe = ProbeType.VERIFY_CLAIM
        else:
            probe = ProbeType.TEST_GAP
        rows.append(
            GapRow(
                skill=s.name,
                jd_weight=s.weight,
                must_have=s.must_have,
                evidence=evidence,
                probe_type=probe,
                priority_score=_score(s.weight, s.must_have, probe),
                claim_id=claim.id if claim and probe is ProbeType.VERIFY_CLAIM else None,
            )
        )
    return sorted(rows, key=lambda r: r.priority_score, reverse=True)


def with_fundamentals(rows: Sequence[GapRow]) -> list[GapRow]:
    """What the interview asks: every row, plus a FUNDAMENTALS row for each skill whose claim is
    verified. Verifying a claim is a walk through the candidate's own project; the extra row asks
    about the skill itself (concepts, how things work, a small problem solved aloud), so a strong
    resume does not turn the whole interview into project discussion (ADR-0023)."""
    extra = [
        r.model_copy(
            update={
                "probe_type": ProbeType.FUNDAMENTALS,
                "priority_score": _score(r.jd_weight, r.must_have, ProbeType.FUNDAMENTALS),
                "claim_id": None,
            }
        )
        for r in rows
        if r.probe_type is ProbeType.VERIFY_CLAIM
    ]
    return sorted([*rows, *extra], key=lambda r: r.priority_score, reverse=True)
