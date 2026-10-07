"""Deterministic planner: split the duration into phase budgets and turn ranked gap rows into a
prioritised topic pool (must / should / bonus). The LLM fills topic *content* later (topic packs);
it never decides budgets or priorities."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from qualifai.content.loader import RoundTemplate, TierPreset
from qualifai.domain.enums import TopicPriority
from qualifai.domain.models import GapRow, InterviewPlan, PhaseBudget, PlannedTopic

DEFAULT_MIN_TOPIC_S = 180


@dataclass(frozen=True, slots=True)
class PlanningConfig:
    must_count: int = 4
    should_count: int = 3
    bonus_count: int = 3
    experience_max_years: int = 5


def allocate_phases(template: RoundTemplate, target_minutes: int) -> tuple[PhaseBudget, ...]:
    total_s = target_minutes * 60
    weight_sum = sum(p.weight for p in template.phases)
    budgets = [
        PhaseBudget(
            name=p.name, seconds=round(total_s * p.weight / weight_sum), reserved=p.reserved
        )
        for p in template.phases
    ]
    drift = total_s - sum(b.seconds for b in budgets)  # put rounding drift in the largest phase
    largest = max(range(len(budgets)), key=lambda i: budgets[i].seconds)
    b = budgets[largest]
    budgets[largest] = PhaseBudget(name=b.name, seconds=b.seconds + drift, reserved=b.reserved)
    return tuple(budgets)


def start_difficulty(tier: TierPreset, experience_max_years: int) -> int:
    base = 2 + tier.difficulty_offset + (1 if experience_max_years >= 6 else 0)
    return max(1, min(4, base))


def build_plan(
    gap_rows: Sequence[GapRow],
    template: RoundTemplate,
    tier: TierPreset,
    target_minutes: int,
    topic_phase: str,
    cfg: PlanningConfig | None = None,
) -> InterviewPlan:
    """MVP: all skill topics go into one content phase (e.g. 'core'); others hold fixed items."""
    cfg = cfg or PlanningConfig()
    phases = allocate_phases(template, target_minutes)
    phase_budget = next(p.seconds for p in phases if p.name == topic_phase)

    ranked = list(gap_rows)[: cfg.must_count + cfg.should_count + cfg.bonus_count]
    priorities = (
        [TopicPriority.MUST] * cfg.must_count
        + [TopicPriority.SHOULD] * cfg.should_count
        + [TopicPriority.BONUS] * cfg.bonus_count
    )
    funded = [r for r, p in zip(ranked, priorities, strict=False) if p is not TopicPriority.BONUS]
    score_sum = sum(r.priority_score for r in funded) or 1.0
    diff = start_difficulty(tier, cfg.experience_max_years)

    topics: list[PlannedTopic] = []
    for i, (row, prio) in enumerate(zip(ranked, priorities, strict=False)):
        budget = (
            round(phase_budget * row.priority_score / score_sum)
            if prio is not TopicPriority.BONUS
            else DEFAULT_MIN_TOPIC_S
        )
        topics.append(
            PlannedTopic(
                id=f"t{i + 1}-{row.skill}",
                phase=topic_phase,
                title=f"{row.probe_type.value.replace('_', ' ')}: {row.skill}",
                skills=(row.skill,),
                priority=prio,
                budget_seconds=max(budget, DEFAULT_MIN_TOPIC_S),
                min_seconds=DEFAULT_MIN_TOPIC_S,
                max_depth=tier.max_depth,
                start_difficulty=diff,
                claim_id=row.claim_id,
            )
        )
    return InterviewPlan(phases=phases, topics=tuple(topics))
