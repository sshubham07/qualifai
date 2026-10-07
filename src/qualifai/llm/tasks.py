"""Every LLM task in the system. Models are routed per task via content/models.yaml (ADR-0004)."""

from enum import StrEnum


class LLMTask(StrEnum):
    # Phase 1 — Prep (quality > speed)
    INTAKE_GATE = "intake_gate"
    RESUME_EXTRACT = "resume_extract"
    JD_EXTRACT = "jd_extract"
    TOPIC_SELECTION = "topic_selection"
    TOPIC_PACK = "topic_pack"
    # Phase 2 — Live (speed matters)
    TURN_ANALYZER = "turn_analyzer"
    QUESTION_GEN = "question_gen"
    CODING_HELPER = "coding_helper"
    # Phase 3 — Evaluation (quality matters most)
    TOPIC_EVAL = "topic_eval"
    CODE_REVIEW = "code_review"
    CONTRADICTION_CHECK = "contradiction_check"
    REPORT_NARRATIVE = "report_narrative"
