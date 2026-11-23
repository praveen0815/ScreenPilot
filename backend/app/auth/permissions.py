from enum import StrEnum

from app.db.enums import UserRole
from app.db.models.agent_task import AgentTask
from app.db.models.user import User


class Permission(StrEnum):
    TASK_READ = "task:read"
    TASK_WRITE = "task:write"
    TASK_DELETE = "task:delete"
    USER_READ_SELF = "user:read_self"
    USER_WRITE_SELF = "user:write_self"
    TOOL_BROWSER = "tool:browser"
    TOOL_DESKTOP = "tool:desktop"
    TOOL_VISION = "tool:vision"
    TOOL_FILESYSTEM = "tool:filesystem"
    PURCHASE_EXECUTE = "purchase:execute"
    ADMIN_ALL = "admin:all"


ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    UserRole.USER: frozenset(
        {
            Permission.TASK_READ,
            Permission.TASK_WRITE,
            Permission.USER_READ_SELF,
            Permission.USER_WRITE_SELF,
            Permission.TOOL_BROWSER,
            Permission.TOOL_DESKTOP,
            Permission.TOOL_VISION,
        }
    ),
    UserRole.ADMIN: frozenset(
        {
            Permission.TASK_READ,
            Permission.TASK_WRITE,
            Permission.TASK_DELETE,
            Permission.USER_READ_SELF,
            Permission.USER_WRITE_SELF,
            Permission.TOOL_BROWSER,
            Permission.TOOL_DESKTOP,
            Permission.TOOL_VISION,
            Permission.ADMIN_ALL,
        }
    ),
}


def has_permission(user: User, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(user.role, frozenset())


def can_access_task(user: User, task: AgentTask) -> bool:
    if user.role is UserRole.ADMIN:
        return True
    return task.user_id == user.id