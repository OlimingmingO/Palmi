"""Dialogue service — manages conversation context and LLM interaction.

Phase 0: Simple in-memory context buffer. No persistence, no persona.
"""
import logging
from typing import Optional

from app.utils.llm import chat_completion

logger = logging.getLogger(__name__)

# In-memory conversation buffer: {elder_id: [messages]}
# Lost on restart — fine for Phase 0
_CONVERSATION_BUFFER: dict[str, list[dict]] = {}
MAX_CONTEXT_MESSAGES = 10


def _get_context(elder_id: str) -> list[dict]:
    """Get conversation context for an elder."""
    return _CONVERSATION_BUFFER.get(elder_id, [])


def _add_message(elder_id: str, role: str, content: str) -> None:
    """Add a message to the conversation buffer."""
    if elder_id not in _CONVERSATION_BUFFER:
        _CONVERSATION_BUFFER[elder_id] = []

    _CONVERSATION_BUFFER[elder_id].append({"role": role, "content": content})

    # Trim to max context length
    if len(_CONVERSATION_BUFFER[elder_id]) > MAX_CONTEXT_MESSAGES:
        _CONVERSATION_BUFFER[elder_id] = _CONVERSATION_BUFFER[elder_id][-MAX_CONTEXT_MESSAGES:]


async def get_reply(elder_id: str, user_message: str) -> str:
    """Process a user message and get an AI reply.

    Args:
        elder_id: UUID string identifying the elder
        user_message: The text message from the user

    Returns:
        AI assistant reply text
    """
    # Add user message to context
    _add_message(elder_id, "user", user_message)

    # Build messages for LLM (no system prompt in Phase 0)
    messages = _get_context(elder_id)

    try:
        reply = await chat_completion(messages=messages)
    except RuntimeError as e:
        logger.error("LLM failed for elder %s: %s", elder_id, str(e))
        reply = "抱歉，我暂时无法回复。请稍后再试。"

    # Add assistant reply to context
    _add_message(elder_id, "assistant", reply)

    return reply
