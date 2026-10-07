"""Coding round controller (V2) — event-driven, deterministic triggers:

* no edits and no message for 3 min → offer hint level N (from the problem's hint ladder)
* repeated failing runs              → nudge toward an edge case
* submit                             → hidden + performance tests (ground truth)
* after submit                       → LLM follow-ups: complexity, edge cases, scaling

Complexity judgement: performance tests decide "efficient enough"; the LLM only labels and
explains Big-O. Disagreement → trust tests, mark the LLM label low-confidence.
"""
