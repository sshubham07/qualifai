"""Judgement-quality eval harness (T-42). Needs a configured model; not part of CI's fast lane.

Plan: an LLM role-plays each simulated candidate (persona from golden/simulated_candidates.yaml)
through the real interview graph; the evaluation pipeline scores it; metrics are checked and
written to tests/evals/results/<timestamp>.json for trend tracking across model/prompt changes.
"""

from pathlib import Path

import yaml

GOLDEN = Path(__file__).parent / "golden" / "simulated_candidates.yaml"


def main() -> None:
    spec = yaml.safe_load(GOLDEN.read_text())
    print(f"Loaded {len(spec['candidates'])} simulated candidates; metrics: {len(spec['metrics'])}")
    raise SystemExit(
        "Eval runner not implemented yet — see .claude/specs/001-mvp-r1-technical/tasks.md T-42"
    )


if __name__ == "__main__":
    main()
