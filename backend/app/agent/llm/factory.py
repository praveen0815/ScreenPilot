from app.agent.llm.mock import MockLLMProvider
from app.agent.llm.protocol import LLMProvider
from app.core.config import get_settings
from app.core.errors import AppError


def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    provider = settings.llm_provider.strip().lower()
    if provider == "mock":
        return MockLLMProvider()
    raise AppError(
        code="llm_unavailable",
        message=(
            f"LLM provider '{settings.llm_provider}' is not enabled. "
            "Phase 3 only ships the mock provider."
        ),
        status_code=501,
    )