import pytest

from app.automation.browser.url_policy import BrowserUrlPolicyError, validate_navigation_url
from app.core.config import get_settings


def test_url_policy_blocks_unsafe_schemes():
    settings = get_settings().model_copy(update={"browser_allow_localhost": False, "app_env": "production"})
    with pytest.raises(BrowserUrlPolicyError):
        validate_navigation_url("javascript:alert(1)", settings)
    with pytest.raises(BrowserUrlPolicyError):
        validate_navigation_url("file:///etc/passwd", settings)


def test_url_policy_blocks_localhost_when_disabled():
    settings = get_settings().model_copy(update={"browser_allow_localhost": False, "app_env": "test"})
    with pytest.raises(BrowserUrlPolicyError):
        validate_navigation_url("http://127.0.0.1:8080/page.html", settings)


def test_url_policy_allows_localhost_in_dev_when_enabled():
    settings = get_settings().model_copy(update={"browser_allow_localhost": True, "app_env": "test"})
    assert validate_navigation_url("http://127.0.0.1:8080/page.html", settings).startswith("http")