"""Explicit keyboard shortcut allowlist — sensitive system combos are denied."""

from app.automation.desktop.errors import DesktopHotkeyDeniedError

_BLOCKED_SUBSTRINGS = frozenset({"win", "windows", "super", "command", "cmd", "meta"})

# Normalized tuples of lowercase key names.
ALLOWED_HOTKEYS: frozenset[tuple[str, ...]] = frozenset(
    {
        ("ctrl", "c"),
        ("ctrl", "v"),
        ("ctrl", "x"),
        ("ctrl", "a"),
        ("ctrl", "z"),
        ("ctrl", "y"),
        ("ctrl", "shift", "z"),
        ("alt", "tab"),
        ("shift", "tab"),
        ("ctrl", "tab"),
        ("ctrl", "w"),
        ("ctrl", "f"),
        ("ctrl", "s"),
        ("enter",),
        ("escape",),
        ("tab",),
        ("shift",),
        ("ctrl",),
        ("alt",),
    }
)


def normalize_hotkey_keys(keys: list[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for raw in keys:
        key = raw.strip().lower().replace(" ", "")
        if not key:
            raise DesktopHotkeyDeniedError("Hotkey contains an empty key.")
        if key in _BLOCKED_SUBSTRINGS or any(blocked in key for blocked in _BLOCKED_SUBSTRINGS):
            raise DesktopHotkeyDeniedError("Hotkey uses a restricted modifier.")
        aliases = {"control": "ctrl", "option": "alt", "return": "enter", "esc": "escape"}
        normalized.append(aliases.get(key, key))
    return tuple(normalized)


def validate_hotkey(keys: list[str]) -> tuple[str, ...]:
    normalized = normalize_hotkey_keys(keys)
    if "alt" in normalized and "f4" in normalized:
        raise DesktopHotkeyDeniedError("Alt+F4 is not allowed.")
    if normalized == ("ctrl", "alt", "delete") or normalized == ("ctrl", "shift", "escape"):
        raise DesktopHotkeyDeniedError("Sensitive shortcut is not allowed.")
    if normalized not in ALLOWED_HOTKEYS:
        raise DesktopHotkeyDeniedError("Shortcut is not on the approved allowlist.")
    return normalized