import re

_POLICY_OVERRIDE_PATTERNS = (
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.I),
    re.compile(r"you\s+are\s+now\s+", re.I),
    re.compile(r"disregard\s+(safety|policy|permissions)", re.I),
    re.compile(r"grant\s+(admin|all)\s+permissions", re.I),
    re.compile(r"set\s+.*permission", re.I),
    re.compile(r"disable\s+(approval|safety)", re.I),
)


def is_policy_override_attempt(text: str) -> bool:
    return any(pattern.search(text) for pattern in _POLICY_OVERRIDE_PATTERNS)


def scrub_untrusted_for_policy(text: str) -> str:
    """Marks injection-like segments without executing them."""
    if not is_policy_override_attempt(text):
        return text
    return f"[untrusted-policy-attempt-blocked] {text[:500]}"