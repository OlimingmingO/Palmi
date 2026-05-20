"""Elder user management — lookup and auto-registration."""
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.elder import Elder


async def get_or_create_elder(db: AsyncSession, wechat_user_id: str) -> Elder:
    """Find elder by WeCom user ID, or create a new one.
    
    Used during message callback to resolve the tenant.
    """
    stmt = select(Elder).where(Elder.wechat_user_id == wechat_user_id)
    result = await db.execute(stmt)
    elder = result.scalar_one_or_none()

    if elder is None:
        elder = Elder(
            id=uuid.uuid4(),
            wechat_user_id=wechat_user_id,
            status="active",
        )
        db.add(elder)
        await db.flush()  # Get the ID without committing

        # Initialize PKE vault for new elder
        from app.pke.pke_service import pke_service
        pke_service.init_vault(str(elder.id))

    return elder


def get_active_elders_sync():
    """Synchronous version for Celery tasks."""
    from app.database import sync_session_factory
    from sqlalchemy import select

    with sync_session_factory() as session:
        stmt = select(Elder).where(Elder.status == "active")
        result = session.execute(stmt)
        return result.scalars().all()
