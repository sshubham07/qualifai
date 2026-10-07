"""Typed settings from environment (prefix QUALIFAI_). See .env.example."""

from functools import cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="QUALIFAI_", env_file=".env", extra="ignore")

    env: str = "local"
    secret_key: SecretStr = SecretStr("change-me")
    base_url: str = "http://localhost:3000"

    database_url: str = "postgresql+asyncpg://qualifai:qualifai@localhost:5432/qualifai"
    redis_url: str = "redis://localhost:6379/0"
    s3_endpoint: str = "http://localhost:9000"
    s3_bucket: str = "qualifai"
    s3_access_key: str = "minio"
    s3_secret_key: SecretStr = SecretStr("minio12345")

    ollama_base_url: str = "http://localhost:11434/v1"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_api_key: SecretStr | None = None
    vllm_base_url: str | None = None
    models_file: str = "content/models.yaml"

    smtp_host: str = "localhost"
    smtp_port: int = 1025
    mail_from: str = "QualifAI <no-reply@qualifai.local>"

    kit_ttl_days: int = 7
    report_retention_days: int = 90
    hard_stop_grace_s: int = 60


@cache
def get_settings() -> Settings:
    return Settings()
