import json
from typing import Any

from app.auth.permissions import ROLE_PERMISSIONS, Permission
from app.db.models.user import User


def _preference_flags(user: User) -> dict[str, Any]:
    prefs = user.agent_preferences
    if prefs is None or not prefs.preferences_json:
        return {}
    try:
        raw = json.loads(prefs.preferences_json)
    except json.JSONDecodeError:
        return {}
    if not isinstance(raw, dict):
        return {}
    return raw


def effective_permissions(user: User) -> frozenset[Permission]:
    """Role grants adjusted by per-user safety preference flags."""
    grants = set(ROLE_PERMISSIONS.get(user.role, frozenset()))
    flags = _preference_flags(user)
    if flags.get("disable_browser"):
        grants.discard(Permission.TOOL_BROWSER)
    if flags.get("disable_desktop"):
        grants.discard(Permission.TOOL_DESKTOP)
    if flags.get("disable_vision"):
        grants.discard(Permission.TOOL_VISION)
    if flags.get("enable_filesystem") is not True:
        grants.discard(Permission.TOOL_FILESYSTEM)
    grants.discard(Permission.PURCHASE_EXECUTE)
    return frozenset(grants)