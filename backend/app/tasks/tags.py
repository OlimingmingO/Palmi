"""tasks.tags.* — Intent classification tasks.

Classifies conversation messages into one of 9 intent categories using LLM.
Called asynchronously after each conversation turn is saved.

Intent taxonomy (9 categories):
  闲聊 / 情感倾诉 / 健康相关 / 购物需求 / 出行需求 / 信息查询 / 任务委托 / 社交相关 / 其他
"""
import asyncio
import json
import logging
import uuid
from typing import Optional

from app.celery_app import celery_app

logger = logging.getLogger(__name__)

# The 9 intent tag names (must match seeds in migration)
INTENT_TAGS = [
    "闲聊",
    "情感倾诉",
    "健康相关",
    "购物需求",
    "出行需求",
    "信息查询",
    "任务委托",
    "社交相关",
    "其他",
]

CLASSIFICATION_SYSTEM_PROMPT = """你是一个对话意图分类器。
你的任务是分析一段老人与AI助手的对话，判断老人这轮发言的主要意图。

可用标签（从以下9个中选择1-2个最匹配的）：
- 闲聊：日常闲聊、问候、天气等轻松话题
- 情感倾诉：表达情绪、心情、孤独、思念等
- 健康相关：身体状况、用药、看病、健康咨询
- 购物需求：买东西、购物相关请求
- 出行需求：打车、出门、交通相关请求
- 信息查询：查天气、查新闻、查知识等
- 任务委托：请求AI帮忙做某件具体的事
- 社交相关：家人、朋友、社区活动相关话题
- 其他：不属于以上分类的内容

请严格按照以下JSON格式输出，不要输出任何其他内容：
{"tags": [{"name": "标签名", "confidence": 0.95}]}

confidence取值0.0-1.0，表示你对该分类的把握程度。"""


def _build_classification_prompt(user_message: str, context: list[tuple[str, str]] = None) -> str:
    """Build the user-turn prompt for intent classification.

    Args:
        user_message: The current user message to classify.
        context: Optional list of (role, content) tuples representing previous turns.
    """
    context_str = ""
    if context:
        context_str = "以下是前几轮对话上下文：\n"
        for role, content in context:
            label = "老人" if role == "user" else "小伴"
            context_str += f"{label}：{content}\n"
        context_str += "\n"
    return f"{context_str}请对以下老人发言进行意图分类：\n\n「{user_message}」"


async def _classify_async(elder_id: str, conversation_id: str) -> None:
    """Async implementation of intent classification."""
    from app.database import async_session_factory
    from app.models.conversation import Conversation
    from app.models.tag import IntentTag, MessageTag
    from app.utils.llm import chat_completion
    from sqlalchemy import select

    async with async_session_factory() as session:
        # 1. Load the conversation record
        stmt = select(Conversation).where(
            Conversation.id == uuid.UUID(conversation_id)
        )
        result = await session.execute(stmt)
        conversation = result.scalar_one_or_none()

        if conversation is None:
            logger.warning("classify_tags: conversation %s not found", conversation_id)
            return

        # Only classify user messages (not assistant replies)
        if conversation.role != "user":
            logger.debug("classify_tags: skipping non-user message %s", conversation_id)
            return

        user_content = conversation.content
        if not user_content or not user_content.strip():
            logger.debug("classify_tags: empty content for %s", conversation_id)
            return

        # 2. Query previous 3 turns for context
        context_stmt = (
            select(Conversation)
            .where(
                Conversation.elder_id == conversation.elder_id,
                Conversation.created_at < conversation.created_at,
            )
            .order_by(Conversation.created_at.desc())
            .limit(3)
        )
        context_result = await session.execute(context_stmt)
        context_rows = list(reversed(context_result.scalars().all()))
        context = [(row.role, row.content) for row in context_rows] if context_rows else None

        # 3. Build classification prompt and call LLM
        messages = [
            {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
            {"role": "user", "content": _build_classification_prompt(user_content, context)},
        ]

        try:
            raw_response = await chat_completion(
                messages=messages,
                temperature=0.0,
                max_tokens=200,
            )
        except Exception as e:
            logger.error("LLM classification failed for %s: %s", conversation_id, e)
            return

        # 4. Parse JSON response
        tag_results = _parse_classification_response(raw_response)
        if not tag_results:
            logger.warning("classify_tags: could not parse LLM response for %s: %s", conversation_id, raw_response[:200])
            return

        # 5. Load tag ID mappings from DB
        tag_stmt = select(IntentTag).where(IntentTag.is_active == True)
        tag_result = await session.execute(tag_stmt)
        tag_map = {tag.name: tag.id for tag in tag_result.scalars().all()}

        # 6. Persist MessageTag records
        for tag_name, confidence in tag_results:
            tag_id = tag_map.get(tag_name)
            if tag_id is None:
                logger.warning("classify_tags: unknown tag '%s', skipping", tag_name)
                continue

            needs_review = confidence < 0.6

            message_tag = MessageTag(
                elder_id=uuid.UUID(elder_id),
                message_id=uuid.UUID(conversation_id),
                tag_id=tag_id,
                confidence=confidence,
                source="llm",
                needs_review=needs_review,
            )
            session.add(message_tag)

        await session.commit()
        logger.debug(
            "classify_tags: tagged message %s with %d tag(s)",
            conversation_id,
            len(tag_results),
        )

        # 7. Trigger unmet-needs detection for this user message
        #    Find the assistant reply that immediately followed this user message.
        try:
            reply_stmt = (
                select(Conversation)
                .where(
                    Conversation.elder_id == conversation.elder_id,
                    Conversation.role == "assistant",
                    Conversation.created_at >= conversation.created_at,
                    Conversation.id != conversation.id,
                )
                .order_by(Conversation.created_at.asc())
                .limit(1)
            )
            reply_result = await session.execute(reply_stmt)
            bot_reply_row = reply_result.scalar_one_or_none()

            if bot_reply_row is not None:
                from app.tasks.unmet import detect_unmet_need

                detect_unmet_need.delay(
                    str(conversation.elder_id),
                    str(conversation.id),
                    user_content,
                    bot_reply_row.content,
                )
            else:
                logger.debug(
                    "classify_tags: no assistant reply yet for %s, skipping unmet detection",
                    conversation_id,
                )
        except Exception as _unmet_err:
            logger.warning("Failed to queue unmet-need detection: %s", _unmet_err)


def _parse_classification_response(raw: str) -> list[tuple[str, float]]:
    """Parse LLM JSON response into list of (tag_name, confidence) tuples.

    Handles cases where LLM wraps JSON in markdown code fences.
    Returns empty list on parse failure.
    """
    text = raw.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last fence lines
        text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
        text = text.strip()

    try:
        data = json.loads(text)
        tags = data.get("tags", [])
        results = []
        for item in tags:
            name = item.get("name", "").strip()
            confidence = float(item.get("confidence", 1.0))
            if name in INTENT_TAGS:
                results.append((name, min(max(confidence, 0.0), 1.0)))
        return results
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        return []


@celery_app.task(
    bind=True,
    name="tasks.tags.classify",
    queue="default",
    max_retries=3,
    default_retry_delay=30,
)
def classify_tags(self, elder_id: str, conversation_id: str):
    """LLM-based intent tag classification for a conversation message.

    Args:
        elder_id: UUID string of the elder
        conversation_id: UUID string of the Conversation record to classify
    """
    try:
        asyncio.run(_classify_async(elder_id, conversation_id))
    except Exception as e:
        logger.error(
            "classify_tags failed for elder=%s conversation=%s: %s",
            elder_id,
            conversation_id,
            e,
        )
        raise self.retry(exc=e)
