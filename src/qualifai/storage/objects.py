"""S3-compatible object storage (MinIO locally). Binary files never go into DB rows."""

import boto3  # type: ignore[import-untyped]

from qualifai.config.settings import get_settings


def client():  # type: ignore[no-untyped-def]
    s = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=s.s3_endpoint,
        aws_access_key_id=s.s3_access_key,
        aws_secret_access_key=s.s3_secret_key.get_secret_value(),
    )


def resume_key(interview_id: str) -> str:
    return f"resumes/{interview_id}.pdf"


def report_key(interview_id: str) -> str:
    return f"reports/{interview_id}.html"
