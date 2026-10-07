"""Context Compiler — builds a small, bounded prompt for every LLM call (ADR-0002).

The prompt size stays roughly constant whether we are at minute 2 or minute 44, because we
never send the whole transcript: only ordered *slices*, dropped lowest-priority-first when
over budget. Static slices go first so provider prefix caching can reuse them.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Slice:
    name: str
    text: str
    priority: int  # lower = more important; 0 = never dropped
    static: bool = False  # cacheable prefix (system rules, candidate brief)


def estimate_tokens(text: str) -> int:
    """Cheap heuristic (~4 chars/token). Good enough for budgeting; swap for a tokenizer later."""
    return max(1, len(text) // 4)


def compile_context(slices: list[Slice], budget_tokens: int) -> tuple[str, list[str]]:
    """Return (prompt, dropped_slice_names). Priority-0 slices are always kept."""
    kept = sorted(slices, key=lambda s: (not s.static, s.priority))
    dropped: list[str] = []
    while sum(estimate_tokens(s.text) for s in kept) > budget_tokens:
        droppable = [s for s in kept if s.priority > 0]
        if not droppable:
            break
        victim = max(droppable, key=lambda s: s.priority)
        kept.remove(victim)
        dropped.append(victim.name)
    prompt = "\n\n".join(f"## {s.name}\n{s.text}" for s in kept)
    return prompt, dropped
