"""Small pure pieces of the live phase: tokens, checkpointer URL, answer limits."""

import pytest
from pydantic import ValidationError

from qualifai.domain.models import Answer, Draft
from qualifai.domain.tokens import hash_token, token_matches
from qualifai.interview.checkpoint import conninfo

pytestmark = pytest.mark.unit


def test_only_the_right_token_matches_its_hash():
    stored = hash_token("the-link-token")
    assert token_matches("the-link-token", stored)
    assert not token_matches("another", stored)
    assert not token_matches(None, stored) and not token_matches("", stored)
    assert "the-link-token" not in stored


def test_checkpointer_gets_a_plain_postgres_url():
    assert conninfo("postgresql+asyncpg://u:p@db:5432/q") == "postgresql://u:p@db:5432/q"
    assert conninfo("postgresql://u:p@db/q") == "postgresql://u:p@db/q"


@pytest.mark.parametrize(
    "bad",
    [
        {"question_seq": 1, "text": ""},
        {"question_seq": 0, "text": "x"},
        {"question_seq": 1, "text": "x" * 8001},
        {"question_seq": 1, "text": "x", "idle_ms": -1},
        {"question_seq": 1, "text": "x", "pastes": [{"at_ms": 1, "chars": 0}]},
        {"question_seq": 1, "text": "x", "pastes": [{"at_ms": 1, "chars": 9}] * 51},
        {"question_seq": 1, "text": "x", "score": 10},  # extra="forbid"
    ],
)
def test_answer_rejects_bad_input(bad):
    with pytest.raises(ValidationError):
        Answer.model_validate(bad)


def test_an_empty_draft_is_allowed_but_not_an_endless_one():
    assert Draft(question_seq=3, text="").text == ""
    with pytest.raises(ValidationError):
        Draft(question_seq=3, text="x" * 8001)
