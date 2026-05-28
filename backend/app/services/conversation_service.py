"""Conversation persistence service — DB-backed message history."""
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation


async def save_message(
    db: AsyncSession,
    elder_id: uuid.UUID,
    role: str,
    content: str,
    channel: Optional[str] = None,
) -> Conversation:
    """Persist a conversation message to the database.

    Args:
        db: Async database session
        elder_id: UUID of the elder
        role: 'user' or 'assistant'
        content: Message text
        channel: Source channel (e.g. 'wecom_kf', 'ilink', 'wecom_app')

    Returns:
        The created Conversation record
    """
    msg = Conversation(
        id=uuid.uuid4(),
        elder_id=elder_id,
        role=role,
        content=content,
        channel=channel,
    )
    db.add(msg)
    await db.flush()
    return msg


async def get_recent(
    db: AsyncSession,
    elder_id: uuid.UUID,
    limit: int = 10,
) -> list[dict]:
    """Get the most recent messages for an elder, ordered chronologically.

    Returns:
        List of {role, content} dicts suitable for LLM context.
    """
    stmt = (
        select(Conversation)
        .where(Conversation.elder_id == elder_id)
        .order_by(Conversation.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()

    # Reverse to chronological order
    messages = list(reversed(messages))

    return [{"role": msg.role, "content": msg.content} for msg in messages]
