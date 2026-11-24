from functools import lru_cache
from typing import Literal

from pydantic import Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.database_url import apply_compose_database_url


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ScreenPilot"
    app_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    database_url: str
    redis_url: str
    cors_origins: str = "http://localhost:5173,http://localhost:8080"
    dependency_check_timeout_seconds: float = Field(default=2.0, gt=0, le=30)
    jwt_secret: str
    jwt_issuer: str = "screenpilot"
    jwt_access_token_expire_minutes: int = Field(default=15, ge=1, le=1440)
    jwt_refresh_token_expire_days: int = Field(default=7, ge=1, le=90)
    llm_provider: str = Field(default="mock", description="LLM adapter: mock only in Phase 3")
    llm_model: str = Field(default="mock-planner-v1")
    llm_api_key: str | None = None
    agent_max_plan_steps: int = Field(default=20, ge=1, le=50)
    tool_default_timeout_seconds: float = Field(default=5.0, gt=0, le=120)
    browser_enabled: bool = False
    browser_headless: bool = True
    browser_chromium_executable: str | None = None
    browser_allow_localhost: bool = False
    browser_navigation_timeout_ms: int = Field(default=30_000, ge=1000, le=120_000)
    browser_action_timeout_ms: int = Field(default=10_000, ge=500, le=60_000)
    browser_wait_max_timeout_ms: int = Field(default=60_000, ge=1000, le=120_000)
    browser_max_text_chars: int = Field(default=8_000, ge=500, le=50_000)
    browser_max_screenshot_bytes: int = Field(default=2_000_000, ge=50_000, le=8_000_000)
    desktop_enabled: bool = False
    desktop_adapter: Literal["mock", "pyautogui"] = "mock"
    desktop_action_timeout_seconds: float = Field(default=10.0, gt=0, le=120)
    desktop_wait_max_ms: int = Field(default=30_000, ge=100, le=120_000)
    desktop_max_screenshot_bytes: int = Field(default=2_000_000, ge=50_000, le=8_000_000)
    vision_enabled: bool = False
    vision_ocr_provider: Literal["mock", "tesseract"] = "mock"
    vision_model_provider: Literal["mock"] = "mock"
    vision_max_image_bytes: int = Field(default=4_000_000, ge=10_000, le=8_000_000)
    vision_max_width: int = Field(default=1920, ge=320, le=3840)
    vision_max_height: int = Field(default=1080, ge=240, le=2160)
    vision_png_compress_level: int = Field(default=6, ge=0, le=9)
    memory_max_entries_per_task: int = Field(default=200, ge=10, le=2000)
    memory_max_chars_per_entry: int = Field(default=4000, ge=100, le=20000)
    memory_context_window_chars: int = Field(default=12000, ge=1000, le=100000)
    memory_recent_tool_results_limit: int = Field(default=10, ge=1, le=100)
    memory_short_term_ttl_hours: int = Field(default=24, ge=1, le=168)
    memory_conversation_ttl_days: int = Field(default=30, ge=1, le=365)
    memory_checkpoint_ttl_days: int = Field(default=14, ge=1, le=90)
    memory_summary_ttl_days: int = Field(default=90, ge=1, le=365)
    memory_retention_cleanup_enabled: bool = True
    approval_expire_hours: int = Field(default=24, ge=1, le=168)
    safety_require_approval_for_moderate: bool = True
    workflow_max_executions_per_run: int = Field(default=100, ge=1, le=500)
    workflow_max_retries_per_step: int = Field(default=3, ge=0, le=10)
    workflow_max_revision_loops: int = Field(default=2, ge=0, le=10)

    @field_validator("database_url")
    @classmethod
    def database_url_must_use_asyncpg(cls, value: str) -> str:
        if not value.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL must use the postgresql+asyncpg driver")
        return value

    @field_validator("redis_url")
    @classmethod
    def redis_url_must_be_redis(cls, value: str) -> str:
        if not value.startswith("redis://"):
            raise ValueError("REDIS_URL must start with redis://")
        return value

    @field_validator("log_level")
    @classmethod
    def log_level_must_be_known(cls, value: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        normalized = value.upper()
        if normalized not in allowed:
            raise ValueError("LOG_LEVEL must be DEBUG, INFO, WARNING, ERROR, or CRITICAL")
        return normalized

    @field_validator("jwt_secret")
    @classmethod
    def jwt_secret_has_minimum_length(cls, value: str, info: ValidationInfo) -> str:
        app_env = info.data.get("app_env", "development")
        if app_env != "test" and len(value) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters outside test")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def _load_settings() -> Settings:
    return Settings()


def get_settings() -> Settings:
    if apply_compose_database_url() is not None:
        _load_settings.cache_clear()
    return _load_settings()


get_settings.cache_clear = _load_settings.cache_clear  # type: ignore[attr-defined]
