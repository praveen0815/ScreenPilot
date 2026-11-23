from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.services.audit_service import record_audit


async def update_profile(session: AsyncSession, user: User, *, display_name: str) -> User:
    user.display_name = display_name.strip()
    await session.flush()
    await record_audit(
        session,
        action="user.profile_update",
        resource_type="user",
        user_id=user.id,
        resource_id=str(user.id),
    )
    return user