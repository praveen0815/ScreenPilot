import ipaddress
import re
from urllib.parse import urlparse

from app.core.config import Settings

_SCHEME_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*$")
_BLOCKED_LITERAL_HOSTS = frozenset(
    {
        "metadata.google.internal",
        "metadata.goog",
    }
)


class BrowserUrlPolicyError(ValueError):
    pass


def validate_css_selector(selector: str) -> str:
    cleaned = selector.strip()
    if not cleaned or len(cleaned) > 500:
        raise BrowserUrlPolicyError("selector must be between 1 and 500 characters.")
    if any(char in cleaned for char in ("\n", "\r", "\0")):
        raise BrowserUrlPolicyError("selector contains unsupported characters.")
    return cleaned


def validate_navigation_url(url: str, settings: Settings) -> str:
    cleaned = url.strip()
    if len(cleaned) > 2000:
        raise BrowserUrlPolicyError("url is too long.")
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"}:
        raise BrowserUrlPolicyError("url must use http or https.")
    if not parsed.netloc or _SCHEME_PATTERN.fullmatch(parsed.scheme) is None:
        raise BrowserUrlPolicyError("url must be absolute.")

    host = parsed.hostname
    if host is None:
        raise BrowserUrlPolicyError("url must include a host.")

    lowered_host = host.lower()
    if lowered_host in _BLOCKED_LITERAL_HOSTS:
        raise BrowserUrlPolicyError("url host is not allowed.")

    is_local = lowered_host in {"localhost", "127.0.0.1", "::1"} or lowered_host.endswith(".localhost")
    allow_local = settings.browser_allow_localhost and settings.app_env in {"development", "test"}
    if is_local and not allow_local:
        raise BrowserUrlPolicyError("localhost navigation is not enabled.")

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return cleaned

    if ip.is_loopback and not allow_local:
        raise BrowserUrlPolicyError("loopback navigation is not enabled.")
    if ip.is_private or ip.is_link_local or ip.is_reserved or ip.is_multicast:
        if not allow_local:
            raise BrowserUrlPolicyError("private or restricted addresses are not allowed.")
    return cleaned