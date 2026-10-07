import pytest

from qualifai.domain.enums import Confidence, TopicStatus
from qualifai.domain.models import DimensionScore, EvidenceQuote, TopicEvaluation
from qualifai.eval.aggregation import aggregate_skills, topic_confidence, topic_score
from qualifai.eval.evidence_check import quote_in_text, verify_evaluation

pytestmark = pytest.mark.unit

TURNS = {
    2: "We used Kubernetes with an HPA on CPU; I wrote the Helm charts myself.",
    4: "Service discovery was through cluster DNS, not Consul.",
}


def ev(
    levels: dict[str, int],
    quote: str = "I wrote the Helm charts myself",
    q: int = 3,
    status: TopicStatus = TopicStatus.ASSESSED,
    skills=("kubernetes",),
) -> TopicEvaluation:
    return TopicEvaluation(
        topic_id="t1",
        skills=skills,
        status=status,
        question_count=q,
        dimensions=tuple(
            DimensionScore(
                dimension=d, level=lv, evidence=(EvidenceQuote(turn_seq=2, quote=quote),)
            )
            for d, lv in levels.items()
        ),
    )


@pytest.mark.parametrize(
    ("quote", "ok"),
    [
        ("I wrote the Helm charts myself", True),
        ("i wrote the helm charts, myself!", True),  # normalisation
        ("I wrote the Helm chart myself", True),  # fuzzy
        ("I designed the whole service mesh", False),  # never said
    ],
)
def test_quote_matching(quote, ok):
    assert quote_in_text(quote, TURNS[2]) is ok


def test_unverifiable_dimensions_are_dropped():
    good = ev({"depth": 3})
    bad = ev({"trade_offs": 4}, quote="I benchmarked Istio against Linkerd")
    merged = good.model_copy(update={"dimensions": good.dimensions + bad.dimensions})
    rep = verify_evaluation(merged, TURNS)
    assert [d.dimension for d in rep.evaluation.dimensions] == ["depth"]
    assert rep.dropped_dimensions == ("trade_offs",)


def test_quote_in_other_turn_still_accepted():
    e = ev({"depth": 3}, quote="Service discovery was through cluster DNS")
    assert verify_evaluation(e, TURNS).dropped_dimensions == ()


def test_topic_score_and_confidence():
    assert topic_score(ev({"a": 4, "b": 2})) == 7.5
    assert topic_score(ev({}).model_copy(update={"dimensions": ()})) is None
    assert topic_confidence(ev({"a": 3}, q=1)) is Confidence.LOW
    assert topic_confidence(ev({"a": 3}, q=2)) is Confidence.MEDIUM
    assert topic_confidence(ev({"a": 3}, q=3)) is Confidence.HIGH
    assert topic_confidence(ev({"a": 3}, status=TopicStatus.PARTIAL)) is Confidence.LOW


def test_skill_aggregation_weights_by_questions_and_skips_not_assessed():
    a = ev({"x": 4}, q=3).model_copy(update={"topic_id": "a"})  # 10.0 × 3
    b = ev({"x": 2}, q=1).model_copy(update={"topic_id": "b"})  # 5.0 × 1
    c = ev({"x": 1}, q=5, status=TopicStatus.NOT_ASSESSED)
    s = aggregate_skills([a, b, c])["kubernetes"]
    assert s.score == 8.75 and s.questions == 4 and s.confidence is Confidence.HIGH
