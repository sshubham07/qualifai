"""Typed loaders for content/*.yaml. Content is versioned in git and reviewed like code."""

from __future__ import annotations

from functools import cache
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from qualifai.domain.enums import CompanyTier, RoleFamily, RoundType, SupportLevel

CONTENT_DIR = Path(__file__).resolve().parents[3] / "content"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PhaseSpec(_Strict):
    name: str
    weight: float = Field(gt=0)
    reserved: bool = False


class RoundTemplate(_Strict):
    id: RoundType
    name: str
    default_minutes: int
    phases: tuple[PhaseSpec, ...]
    rubric_dimensions: tuple[str, ...]
    needs_editor: bool = False
    needs_sandbox: bool = False
    scored: bool = True
    rules: str


class TierPreset(_Strict):
    id: CompanyTier
    name: str
    difficulty_offset: int = Field(ge=-1, le=2)
    max_depth: int = Field(ge=1, le=5)
    challenge_threshold: float = Field(ge=0, le=1)
    must_have_floor: float = 5.0
    bands: dict[str, float]  # strong_hire / hire / lean_hire / lean_no_hire thresholds (/10)
    guidance: str


class RoleFamilySpec(_Strict):
    id: RoleFamily
    support: SupportLevel
    rounds: tuple[RoundType, ...]
    skills: dict[str, int]  # skill -> default weight 1..3
    coding_round: bool


def _load(path: Path) -> dict:  # type: ignore[type-arg]
    return yaml.safe_load(path.read_text())  # type: ignore[no-any-return]


@cache
def round_template(round_type: RoundType) -> RoundTemplate:
    return RoundTemplate.model_validate(_load(CONTENT_DIR / "rounds" / f"{round_type.value}.yaml"))


@cache
def tier_preset(tier: CompanyTier) -> TierPreset:
    return TierPreset.model_validate(_load(CONTENT_DIR / "tiers" / f"{tier.value}.yaml"))


@cache
def role_family(family: RoleFamily) -> RoleFamilySpec | None:
    path = CONTENT_DIR / "role_families" / f"{family.value}.yaml"
    return RoleFamilySpec.model_validate(_load(path)) if path.exists() else None


@cache
def skill_aliases() -> dict[str, str]:
    """alias (lowercase) -> canonical skill id, from content/skills/_taxonomy.yaml."""
    raw = _load(CONTENT_DIR / "skills" / "_taxonomy.yaml")
    out: dict[str, str] = {}
    for canonical, spec in raw["skills"].items():
        out[canonical] = canonical
        for alias in spec.get("aliases", []):
            out[alias.lower()] = canonical
    return out


@cache
def seed_anchors(skill: str) -> str:
    """Compact text rendering of content/skills/<skill>.yaml for prompts ('' if no seed bank).
    Missing seed bank → topic is generated 'unanchored' and flagged lower-confidence (ADR-0011)."""
    path = CONTENT_DIR / "skills" / f"{skill}.yaml"
    if not path.exists():
        return ""
    raw = _load(path)
    lines: list[str] = []
    for sub in raw.get("subtopics", []):
        lines.append(f"* {sub['name']}")
        for lvl, text in sub.get("levels", {}).items():
            lines.append(f"  - L{lvl}: {text}")
        if sub.get("red_flags"):
            lines.append(f"  - red flags: {'; '.join(sub['red_flags'])}")
    return "\n".join(lines)
