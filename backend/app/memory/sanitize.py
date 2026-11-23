import base64
import json
import re
from typing import Any

from app.memory.errors import MemoryPolicyError

_SENSITIVE_KEY = re.compile(r"(password|passwd|secret|token|api[_-]?key|credential|authorization|bearer)", re.I)
_BASE64_FIELD = re.compile(r"(image_base64|screenshot|data_base64)", re.I)
_JWT_LIKE = re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")


def sanitize_text_for_memory(text: str, *, max_chars: int) -> str:
    if not text:
        return ""
    cleaned = text
    if _JWT_LIKE.search(cleaned):
        raise MemoryPolicyError("Refusing to store token-like content in memory.")
    lowered = cleaned.lower()
    if "password=" in lowered or "bearer " in lowered:
        raise MemoryPolicyError("Refusing to store credential-like content in memory.")
    cleaned = re.sub(r"([A-Za-z0-9+/]{200,}={0,2})", "[redacted-base64]", cleaned)
    return cleaned[:max_chars]


def sanitize_mapping_for_memory(data: dict[str, Any], *, max_chars: int) -> str:
    redacted: dict[str, Any] = {}
    for key, value in data.items():
        key_str = str(key)
        if _SENSITIVE_KEY.search(key_str) or _BASE64_FIELD.search(key_str):
            redacted[key_str] = "[redacted]"
            continue
        if isinstance(value, str) and len(value) > 300 and _looks_like_base64(value):
            redacted[key_str] = "[redacted-binary]"
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            redacted[key_str] = value
        else:
            redacted[key_str] = str(value)[:200]
    payload = json.dumps(redacted, ensure_ascii=True)
    return sanitize_text_for_memory(payload, max_chars=max_chars)


def _looks_like_base64(value: str) -> bool:
    try:
        if len(value) < 80:
            return False
        decoded = base64.b64decode(value, validate=True)
        return len(decoded) > 64
    except Exception:
        return False


ALLOWED_PREFERENCE_KEYS = frozenset(
    {
        "tone",
        "verbosity",
        "language",
        "planner_style",
        "default_approval_mode",
    }
)


def sanitize_preferences(raw: dict[str, str]) -> dict[str, str]:
    cleaned: dict[str, str] = {}
    for key, value in raw.items():
        if key not in ALLOWED_PREFERENCE_KEYS:
            raise MemoryPolicyError(f"Preference '{key}' is not allowed.")
        if _SENSITIVE_KEY.search(key) or _SENSITIVE_KEY.search(value):
            raise MemoryPolicyError("Preference key or value is not allowed.")
        cleaned[key] = value.strip()[:120]
    return cleaned