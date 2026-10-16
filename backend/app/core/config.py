from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+psycopg://notice:notice@localhost:5432/notice"
    cors_origins: str = "http://localhost:5173"
    public_base_url: str = "http://localhost:5173"
    cookie_secure: bool = False
    docs_enabled: bool = True
    timezone: str = "Asia/Kathmandu"

    session_idle_minutes: int = 120
    session_absolute_hours: int = 12
    login_max_failures: int = 5
    login_lock_minutes: int = 15
    login_ip_max_failures: int = 20

    # Email. EMAIL_MODE=dry_run never opens an SMTP connection.
    email_mode: Literal["dry_run", "smtp"] = "dry_run"
    smtp_host: str = "smtp.hostinger.com"
    smtp_port: int = 465
    smtp_use_ssl: bool = True
    smtp_starttls: bool = False
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "it@gohimalaya.travel"
    smtp_from_name: str = "Shangri La Tours"
    smtp_timeout_seconds: int = 30
    # Placeholders: set from the verified Hostinger plan limits before enabling broadcasts.
    email_rate_per_minute: int = 20
    email_rate_per_day: int = 300
    email_max_attempts: int = 4
    email_backoff_base_seconds: int = 60
    email_backoff_max_seconds: int = 3600
    email_sending_stale_minutes: int = 10
    worker_poll_seconds: int = 5
    test_send_per_hour: int = 10

    attachment_dir: str = "./data/attachments"
    attachment_max_mb: int = 20  # per upload; phone photos are re-compressed
    attachment_max_total_mb: int = 15
    attachment_mode: Literal["link", "attach"] = "link"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def _production_guards(self):
        if self.env == "production":
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE must be true in production")
            if self.docs_enabled:
                raise ValueError("DOCS_ENABLED must be false in production")
            if self.email_mode == "smtp" and not (self.smtp_username and self.smtp_password):
                raise ValueError("SMTP_USERNAME/SMTP_PASSWORD required when EMAIL_MODE=smtp")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
