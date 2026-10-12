"""Domain errors — mapped to HTTP responses in qualifai.api.errors."""

from qualifai.domain.enums import FailureCode


class QualifAIError(Exception):
    """Base error."""


class InterviewStateError(QualifAIError):
    """Illegal lifecycle transition (e.g. starting an expired interview)."""


class InterviewNotFound(QualifAIError):
    """No interview with this meet id."""


class NotInterviewOwner(QualifAIError):
    """The interview was sent to an email address and the link's token is missing or wrong."""


class LLMOutputError(QualifAIError):
    """Model returned output that failed schema validation after retries."""


class SpeechUnavailable(QualifAIError):
    """The speech model could not voice a question; the page falls back to its own voice."""


class PrepRejected(QualifAIError):
    """Prep decided not to build a kit. The interview becomes FAILED with this code and reason."""

    def __init__(self, code: FailureCode, reason: str | None = None) -> None:
        super().__init__(reason or code.value)
        self.code = code
        self.reason = reason
