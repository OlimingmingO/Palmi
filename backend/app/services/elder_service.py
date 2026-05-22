"""Elder user management — lookup and auto-registration."""
import logging
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.elder import Elder

logger = logging.getLogger(__name__)


async def get_or_create_elder(db: AsyncSession, wechat_user_id: str) -> Elder:
    """Find elder by WeCom user ID, or create a new one.

    Resolution strategy:
    1. Exact match on wechat_user_id (handles already-bound and returning users)
    2. Nickname matching: if a web-created elder (placeholder wechat_user_id starting
       with 'web_') has the same nickname as the WeCom user's display name, auto-bind.
    3. If no match, create a new elder record.
    """
    # 1. Exact lookup
    stmt = select(Elder).where(Elder.wechat_user_id == wechat_user_id)
    result = await db.execute(stmt)
    elder = result.scalar_one_or_none()
    if elder:
        return elder

    # 2. Nickname matching — fetch WeCom user's display name
    from app.gateway.wecom_api import get_user_name
    display_name = await get_user_name(wechat_user_id)

    if display_name:
        # Look for unbound web-created elders with exact nickname match
        match_stmt = (
            select(Elder)
            .where(
                Elder.wechat_user_id.like("web_%"),
                Elder.nickname == display_name,
            )
        )
        candidates = (await db.execute(match_stmt)).scalars().all()
        if len(candidates) == 1:
            # Exactly one match — auto-bind
            candidates[0].wechat_user_id = wechat_user_id
            await db.flush()
            logger.info(
                "Auto-bound elder %s ('%s') to WeCom user %s via nickname match",
                candidates[0].id, display_name, wechat_user_id,
            )
            return candidates[0]
        elif len(candidates) > 1:
            logger.warning(
                "Multiple unbound elders match nickname '%s' — skipping auto-bind for WeCom user %s",
                display_name, wechat_user_id,
            )

    # 3. No match — create new elder
    elder = Elder(
        id=uuid.uuid4(),
        wechat_user_id=wechat_user_id,
        nickname=display_name,  # Use WeCom display name if available
        status="active",
    )
    db.add(elder)
    await db.flush()

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
