import uuid

from app.auth.permissions import Permission, can_access_task, has_permission
from app.db.enums import UserRole
from app.db.models.agent_task import AgentTask
from app.db.models.user import User


def test_role_permissions():
    user = User(email="u@example.com", password_hash="x", display_name="U", role=UserRole.USER)
    admin = User(email="a@example.com", password_hash="x", display_name="A", role=UserRole.ADMIN)
    assert has_permission(user, Permission.TASK_WRITE)
    assert not has_permission(user, Permission.ADMIN_ALL)
    assert has_permission(admin, Permission.ADMIN_ALL)


def test_can_access_task_is_user_scoped():
    owner_id = uuid.uuid4()
    other_id = uuid.uuid4()
    owner = User(
        id=owner_id,
        email="o@example.com",
        password_hash="x",
        display_name="O",
        role=UserRole.USER,
    )
    other = User(
        id=other_id,
        email="p@example.com",
        password_hash="x",
        display_name="P",
        role=UserRole.USER,
    )
    task = AgentTask(user_id=owner.id, instruction="x")
    assert can_access_task(owner, task)
    assert not can_access_task(other, task)