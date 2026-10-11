"""Resume ↔ JD match — deterministic (ADR-0018). Before any question is written, code checks that
the resume shows at least something the JD asks for. Only a pair that is totally off stops prep,
with a reason that names the skills; a partial fit goes ahead and its gaps become questions."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from qualifai.domain.enums import EvidenceLevel, FailureCode
from qualifai.domain.models import GapRow, MatchReport

_NAMED = 5  # skills listed in the reason


def mentions(text: str, names: Sequence[str]) -> bool:
    """True if `text` names any of `names` as a whole word ("REST APIs" mentions "api")."""
    return any(
        re.search(rf"(?<![a-z0-9]){re.escape(n)}(?:s|es)?(?![a-z0-9])", text) for n in names if n
    )


def _names(skill: str, aliases: Mapping[str, str]) -> list[str]:
    """Every way the taxonomy knows to write a skill: its id as words plus its aliases."""
    return [skill.replace("_", " "), *(a for a, canonical in aliases.items() if canonical == skill)]


def assess_match(
    rows: Sequence[GapRow], resume_text: str = "", aliases: Mapping[str, str] | None = None
) -> MatchReport:
    """`rows` cover every JD skill, including those outside the taxonomy. A skill is shown if a
    claim carries it or the resume text names it: the extraction model does not tag every skill
    a sentence mentions, and a missed tag must not fail an interview."""
    text, aliases = resume_text.lower(), aliases or {}
    shown = [
        r.evidence is not EvidenceLevel.NONE or mentions(text, _names(r.skill, aliases))
        for r in rows
    ]
    total = sum(r.jd_weight for r in rows)
    got = sum(r.jd_weight for r, ok in zip(rows, shown, strict=True) if ok)
    return MatchReport(
        score=round(got / total, 3) if total else 0.0,
        matched=tuple(r.skill for r, ok in zip(rows, shown, strict=True) if ok),
        missing=tuple(r.skill for r, ok in zip(rows, shown, strict=True) if not ok),
    )


def decide_match(report: MatchReport) -> FailureCode | None:
    """Stop only when nothing overlaps. The score is kept for the record, not for the decision."""
    return None if report.matched else FailureCode.RESUME_JD_NO_MATCH


def _listed(skills: Sequence[str]) -> str:
    shown = ", ".join(s.replace("_", " ") for s in skills[:_NAMED])
    return f"{shown} and {len(skills) - _NAMED} more" if len(skills) > _NAMED else shown


def match_reason(report: MatchReport) -> str:
    """The sentence the candidate reads, naming what the JD asks for and the resume lacks."""
    return (
        f"The resume shows none of the skills this job description asks for "
        f"({_listed(report.missing)}), so there was nothing of yours to interview you on. "
        "Try a job description closer to your experience."
    )
