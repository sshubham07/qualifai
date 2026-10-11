"""Closed vocabularies used across the system."""

from enum import StrEnum


class RoundType(StrEnum):
    R1_TECHNICAL = "r1_technical"  # project deep-dive + core skills (+ DSA in V2)
    R2_LLD = "r2_lld"
    R3_HLD = "r3_hld"
    R4_MANAGERIAL = "r4_managerial"
    HR = "hr"


class CompanyTier(StrEnum):
    SERVICE = "service"
    STARTUP = "startup"
    PRODUCT = "product"
    MAANG = "maang"


class RoleFamily(StrEnum):
    BACKEND_SDE = "backend_sde"
    FULLSTACK = "fullstack"
    FRONTEND = "frontend"
    DATA_ENG = "data_eng"
    DEVOPS = "devops"
    INTEGRATION = "integration"
    QA = "qa"
    ML_ENG = "ml_eng"
    NON_TECHNICAL = "non_technical"
    UNKNOWN = "unknown"


class SupportLevel(StrEnum):
    FULL = "full"
    PARTIAL = "partial"  # "limited mode": no coding round
    UNSUPPORTED = "unsupported"


class InterviewStatus(StrEnum):
    SUBMITTED = "submitted"
    PREPARING = "preparing"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    EVALUATING = "evaluating"
    REPORT_READY = "report_ready"
    FAILED = "failed"
    EXPIRED = "expired"


class FailureCode(StrEnum):
    """Why an interview is FAILED. Stored on the interview and shown to the candidate."""

    NOT_A_RESUME = "not_a_resume"
    NOT_A_JD = "not_a_jd"
    RESUME_NOT_SOFTWARE = "resume_not_software"
    JD_NOT_SOFTWARE = "jd_not_software"
    UNDECIDED = "undecided"  # the intake model was unsure or returned nothing usable
    NO_KNOWN_SKILLS = "no_known_skills"
    PREP_ERROR = "prep_error"


class EndReason(StrEnum):
    NATURAL = "natural"
    EARLY_COMPLETE = "early_complete"
    HARD_STOP = "hard_stop"
    ABANDONED = "abandoned"


class TopicPriority(StrEnum):
    MUST = "must"
    SHOULD = "should"
    BONUS = "bonus"


class TopicStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    ASSESSED = "assessed"
    PARTIAL = "partial"  # opened, cut short by time
    NOT_ASSESSED = "not_assessed"


class ProbeType(StrEnum):
    VERIFY_CLAIM = "verify_claim"  # high JD weight + strong resume claim
    TEST_GAP = "test_gap"  # high JD weight + weak/no evidence
    LIGHT = "light"  # low JD weight


class EvidenceLevel(StrEnum):
    NONE = "none"
    MENTIONED = "mentioned"
    PROJECT = "project"
    DEEP_OWNERSHIP = "deep_ownership"


class AnswerIntent(StrEnum):
    ANSWER = "answer"
    CLARIFICATION_REQUEST = "clarification_request"
    DONT_KNOW = "dont_know"
    OFF_TOPIC = "off_topic"
    REDIRECT_ATTEMPT = "redirect_attempt"  # tries to steer / prompt-inject


class Specificity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ClaimConsistency(StrEnum):
    CONSISTENT = "consistent"
    INFLATED = "inflated"
    CONTRADICTS = "contradicts"
    UNKNOWN = "unknown"


class ClaimVerdict(StrEnum):
    VERIFIED = "verified"
    PARTIAL = "partial"
    CONTRADICTED = "contradicted"
    UNTESTED = "untested"


class PolicyAction(StrEnum):
    FOLLOW_UP_DEEPER = "follow_up_deeper"
    CLARIFY_MISSING = "clarify_missing"
    PROBE_SPECIFICITY = "probe_specificity"
    CHALLENGE_CLAIM = "challenge_claim"
    SCAFFOLD = "scaffold"
    REPHRASE_QUESTION = "rephrase_question"  # candidate asked for clarification
    REDIRECT_BACK = "redirect_back"  # candidate tried to steer the interview
    NEXT_TOPIC = "next_topic"
    CLOSE_TOPIC_TIME = "close_topic_time"
    WRAP_UP = "wrap_up"
    END = "end"


class TimeZone(StrEnum):
    """Where 'now' sits inside the flexible interview window (ADR-0012)."""

    NORMAL = "normal"
    CLOSING = "closing"  # soft_start .. target_end
    OVERTIME = "overtime"  # target_end .. hard_end
    EXPIRED = "expired"  # >= hard_end


class HiringBand(StrEnum):
    STRONG_HIRE = "strong_hire"
    HIRE = "hire"
    LEAN_HIRE = "lean_hire"
    LEAN_NO_HIRE = "lean_no_hire"
    NO_HIRE = "no_hire"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ReadinessLabel(StrEnum):
    READY = "Ready"
    ALMOST_READY = "Almost ready"
    NEEDS_PREPARATION = "Needs preparation"
    INCOMPLETE = "Incomplete interview"


class Confidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
