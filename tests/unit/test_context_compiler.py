import pytest

from qualifai.interview.context_compiler import Slice, compile_context, estimate_tokens

pytestmark = pytest.mark.unit


def test_keeps_everything_under_budget():
    prompt, dropped = compile_context([Slice("a", "x" * 40, 0), Slice("b", "y" * 40, 2)], 100)
    assert dropped == [] and "## a" in prompt and "## b" in prompt


def test_drops_lowest_priority_first_and_never_priority_zero():
    slices = [
        Slice("rules", "r" * 400, 0, static=True),
        Slice("rubric", "u" * 400, 0),
        Slice("extra", "e" * 400, 3),
        Slice("brief", "b" * 400, 1),
    ]
    prompt, dropped = compile_context(slices, budget_tokens=250)
    assert dropped == ["extra", "brief"]
    assert "## rules" in prompt and "## rubric" in prompt


def test_static_slices_come_first_for_prefix_caching():
    prompt, _ = compile_context(
        [Slice("dynamic", "d", 0), Slice("static", "s", 1, static=True)], 100
    )
    assert prompt.index("## static") < prompt.index("## dynamic")


def test_estimate_tokens():
    assert estimate_tokens("abcd" * 10) == 10
