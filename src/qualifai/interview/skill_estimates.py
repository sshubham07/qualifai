"""Running per-skill estimate used only for live difficulty adaptation (not for the report)."""


def update_estimate(current: float, coverage_ratio: float, alpha: float = 0.4) -> float:
    """Exponential moving average on a 1–4 scale. Simple on purpose — no IRT."""
    observed = 1 + 3 * coverage_ratio
    return round((1 - alpha) * current + alpha * observed, 2)


def clamp_difficulty(level: int) -> int:
    return max(1, min(4, level))
