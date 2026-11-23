from app.auth.permissions import Permission
from app.tools.contracts import ToolMetadata


def required_tool_permissions(metadata: ToolMetadata) -> frozenset[Permission]:
    perms = set(metadata.required_permissions)
    name = metadata.name
    if name.startswith("tool.browser."):
        perms.add(Permission.TOOL_BROWSER)
    elif name.startswith("tool.desktop."):
        perms.add(Permission.TOOL_DESKTOP)
    elif name.startswith("tool.vision."):
        perms.add(Permission.TOOL_VISION)
    elif name.startswith("tool.filesystem."):
        perms.add(Permission.TOOL_FILESYSTEM)
    return frozenset(perms)