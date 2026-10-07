"""Domain errors — mapped to HTTP responses in qualifai.api.errors."""


class QualifAIError(Exception):
    """Base error."""


class UnsupportedRoleError(QualifAIError):
    def __init__(self, role_family: str) -> None:
        super().__init__(f"Role family '{role_family}' is not supported yet")
        self.role_family = role_family


class InvalidDocumentError(QualifAIError):
    """Upload is not a resume / JD, empty, or too large."""


class InterviewStateError(QualifAIError):
    """Illegal lifecycle transition (e.g. starting an expired interview)."""


class LLMOutputError(QualifAIError):
    """Model returned output that failed schema validation after retries."""
