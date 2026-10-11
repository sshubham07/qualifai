"""Domain errors — mapped to HTTP responses in qualifai.api.errors."""


class QualifAIError(Exception):
    """Base error."""


class InterviewStateError(QualifAIError):
    """Illegal lifecycle transition (e.g. starting an expired interview)."""


class LLMOutputError(QualifAIError):
    """Model returned output that failed schema validation after retries."""
