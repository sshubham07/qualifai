"""Evidence check — every LLM score must cite a quote that really exists in the transcript.
Dimensions whose quotes can't be found are dropped. Cheap, deterministic hallucination guard."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from difflib import SequenceMatcher

from qualifai.domain.models import DimensionScore, EvidenceQuote, TopicEvaluation

FUZZY_THRESHOLD = 0.85
_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[\"'“”‘’`.,;:!?()\[\]]")


def _norm(text: str) -> str:
    return _WS.sub(" ", _PUNCT.sub("", text.lower())).strip()


def quote_in_text(quote: str, text: str) -> bool:
    q, t = _norm(quote), _norm(text)
    if not q:
        return False
    if q in t:
        return True
    q_words, t_words = q.split(), t.split()
    n = len(q_words)
    if n == 0 or n > len(t_words):
        return False
    for i in range(len(t_words) - n + 1):
        window = " ".join(t_words[i : i + n])
        if SequenceMatcher(None, q, window).ratio() >= FUZZY_THRESHOLD:
            return True
    return False


def quote_exists(q: EvidenceQuote, candidate_turns: Mapping[int, str]) -> bool:
    """Prefer the cited turn; accept any candidate turn of the topic (LLMs mis-number turns)."""
    cited = candidate_turns.get(q.turn_seq)
    if cited is not None and quote_in_text(q.quote, cited):
        return True
    return any(quote_in_text(q.quote, t) for t in candidate_turns.values())


@dataclass(frozen=True, slots=True)
class EvidenceReport:
    evaluation: TopicEvaluation
    dropped_dimensions: tuple[str, ...]
    invalid_quotes: int


def verify_evaluation(ev: TopicEvaluation, candidate_turns: Mapping[int, str]) -> EvidenceReport:
    kept: list[DimensionScore] = []
    dropped: list[str] = []
    invalid = 0
    for dim in ev.dimensions:
        valid = tuple(q for q in dim.evidence if quote_exists(q, candidate_turns))
        invalid += len(dim.evidence) - len(valid)
        if valid:
            kept.append(dim.model_copy(update={"evidence": valid}))
        else:
            dropped.append(dim.dimension)
    return EvidenceReport(
        evaluation=ev.model_copy(update={"dimensions": tuple(kept)}),
        dropped_dimensions=tuple(dropped),
        invalid_quotes=invalid,
    )
