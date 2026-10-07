"""Gap matrix — deterministic. For every JD skill: how strong is the resume evidence, and
therefore what should the interview do with it?

    high JD weight + strong claim   → VERIFY_CLAIM  ("You designed X — walk me through it")
    high JD weight + weak/no claim  → TEST_GAP      (JD needs PostgreSQL, resume barely shows it)
    low JD weight                   → LIGHT
"""

from __future__ import annotations

from collections.abc import Sequence

from qualifai.domain.enums import EvidenceLevel, ProbeType
from qualifai.domain.models import GapRow, JDSkill, ResumeClaim

_EVIDENCE_RANK = {
    EvidenceLevel.NONE: 0,
    EvidenceLevel.MENTIONED: 1,
    EvidenceLevel.PROJECT: 2,
    EvidenceLevel.DEEP_OWNERSHIP: 3,
}
# How valuable is probing, per probe type (verifying a strong claim is the most informative).
_PROBE_FACTOR = {ProbeType.VERIFY_CLAIM: 1.2, ProbeType.TEST_GAP: 1.0, ProbeType.LIGHT: 0.4}


def strongest_claim(skill: str, claims: Sequence[ResumeClaim]) -> ResumeClaim | None:
    relevant = [c for c in claims if skill in c.skills]
    return max(relevant, key=lambda c: _EVIDENCE_RANK[c.evidence_level], default=None)


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
        score = s.weight * _PROBE_FACTOR[probe] * (1.5 if s.must_have else 1.0)
        rows.append(
            GapRow(
                skill=s.name,
                jd_weight=s.weight,
                must_have=s.must_have,
                evidence=evidence,
                probe_type=probe,
                priority_score=round(score, 3),
                claim_id=claim.id if claim and probe is ProbeType.VERIFY_CLAIM else None,
            )
        )
    return sorted(rows, key=lambda r: r.priority_score, reverse=True)
