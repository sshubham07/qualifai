"""Contract tests: recorded model outputs must validate; obviously bad outputs must be rejected.
Re-record fixtures when a prompt or model changes (keeps prompts and schemas in sync)."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from qualifai.domain.models import TopicEvaluation, TurnSignals

pytestmark = pytest.mark.contract
FX = Path(__file__).parent / "fixtures"


def load(name: str) -> dict:
    return json.loads((FX / name).read_text())


def test_turn_signals_fixture_validates():
    assert TurnSignals.model_validate(load("turn_signals_ok.json")).coverage_ratio == 0.67


@pytest.mark.parametrize(
    "patch",
    [
        {"coverage_ratio": 1.7},
        {"intent": "decide_next_question"},  # analyzer must not invent decisions
        {"unexpected": "field"},  # extra="forbid"
    ],
)
def test_turn_signals_rejects_bad_output(patch):
    with pytest.raises(ValidationError):
        TurnSignals.model_validate({**load("turn_signals_ok.json"), **patch})


def test_topic_eval_fixture_validates():
    ev = TopicEvaluation.model_validate(load("topic_eval_ok.json"))
    assert ev.dimensions[0].evidence[0].quote


@pytest.mark.parametrize("level", [0, 5, 10])
def test_topic_eval_rejects_off_scale_levels(level):
    bad = load("topic_eval_ok.json")
    bad["dimensions"][0]["level"] = level
    with pytest.raises(ValidationError):
        TopicEvaluation.model_validate(bad)
