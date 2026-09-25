from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT / ".env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///./newsletter_builder.db"
    cors_origins: str = "http://localhost:3000"
    web_app_url: str = "http://localhost:3000"
    upload_dir: str = "uploads"

    demo_bader_token: str = "bader-demo-token"
    demo_lead_token: str = "lead-demo-token"
    default_workspace_plan: str = "premium"

    slack_bot_token: str = ""
    slack_signing_secret: str = ""
    slack_lead_channel: str = "#newsletter-reviews"

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_tls: bool = True

    mailchimp_api_key: str = ""
    mailchimp_server_prefix: str = "us1"
    mailchimp_list_id: str = ""
    mailchimp_from_name: str = "Newsletter"
    mailchimp_reply_to: str = "noreply@example.com"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-5"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[1] / path
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()
