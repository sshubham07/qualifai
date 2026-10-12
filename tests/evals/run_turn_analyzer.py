"""Run the Turn Analyzer on the hand-written answers in golden/turn_analyzer_answers.yaml and
check that the signals look sensible. Needs the configured live model (content/models.yaml).

    uv run python -m tests.evals.run_turn_analyzer
"""

import asyncio
import sys
from pathlib import Path
from typing import Any

import yaml

from qualifai.container import get_llm
from qualifai.domain.models import PlannedTopic, Rubric, TurnSignals
from qualifai.interview.turn_analyzer import TurnAnalyzer

GOLDEN = Path(__file__).parent / "golden" / "turn_analyzer_answers.yaml"


def problems(signals: TurnSignals, expect: dict[str, Any]) -> list[str]:
    out = []
    for field in ("intent", "specificity", "consistency"):
        if field in expect and getattr(signals, field) != expect[field]:
            out.append(f"{field}={getattr(signals, field).value}, expected {expect[field]}")
    low, high = expect["coverage"]
    if not low <= signals.coverage_ratio <= high:
        out.append(f"coverage={signals.coverage_ratio}, expected {low}–{high}")
    return out


async def main() -> int:
    spec = yaml.safe_load(GOLDEN.read_text())
    topic = PlannedTopic(
        id="t1",
        phase="core",
        title=spec["topic"]["title"],
        skills=("kubernetes",),
        priority="must",
        budget_seconds=420,
        min_seconds=180,
        max_depth=spec["topic"]["max_depth"],
        start_difficulty=2,
        rubric=Rubric(expected_points=tuple(spec["topic"]["rubric"])),
    )
    analyzer, failed = TurnAnalyzer(get_llm()), 0
    for case in spec["cases"]:
        signals = await analyzer.analyze(
            topic=topic,
            candidate_brief="Backend engineer, about 4 years.",
            round_rules="Technical interviewer. Verify resume claims. Never reveal answers.",
            recent_turns=f"Q: {spec['question']}",
            claim_text=spec["claim"],
            answer=case["answer"],
        )
        bad = problems(signals, case["expect"])
        failed += bool(bad)
        print(f"\n{'FAIL' if bad else 'ok  '}  {case['name']}")
        print(
            f"      intent={signals.intent.value} coverage={signals.coverage_ratio} "
            f"specificity={signals.specificity.value} consistency={signals.consistency.value}"
        )
        print(
            f"      covered={len(signals.rubric_points_covered)} "
            f"missing={len(signals.rubric_points_missing)} hooks={list(signals.hooks)}"
        )
        print(f"      follow-up: {signals.proposed_follow_up}")
        for line in bad:
            print(f"      ✗ {line}")
    print(f"\n{len(spec['cases']) - failed}/{len(spec['cases'])} look sensible")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
