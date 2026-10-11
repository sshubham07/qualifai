"""The sentence a candidate reads for each failure code."""

from qualifai.domain.enums import FailureCode

FAILURE_REASONS: dict[FailureCode, str] = {
    FailureCode.NOT_A_RESUME: "The resume text doesn't look like a resume.",
    FailureCode.NOT_A_JD: "The job description text doesn't look like a job description.",
    FailureCode.RESUME_NOT_SOFTWARE: (
        "The resume isn't for a software engineering role. "
        "QualifAI only runs software engineering interviews."
    ),
    FailureCode.JD_NOT_SOFTWARE: (
        "The job description isn't for a software engineering role. "
        "QualifAI only runs software engineering interviews."
    ),
    FailureCode.UNDECIDED: (
        "We couldn't tell whether the resume and the job description are for a software "
        "engineering role, so we stopped before preparing questions."
    ),
    FailureCode.NO_KNOWN_SKILLS: (
        "The job description lists no skills we can ask about yet, so there was nothing to "
        "build an interview from."
    ),
    FailureCode.PREP_ERROR: "Something went wrong on our side while preparing the interview.",
}
