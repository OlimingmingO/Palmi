"""tasks.trigger.* — Proactive trigger evaluation and delivery tasks.

Task naming: tasks.trigger.*
Queue: high_priority

Phase 2: 15-minute evaluation loop that checks all 4 trigger types
(calendar, weather, memory, time_gap) for each active elder and
sends a proactive message if conditions are met and frequency
limits allow.
"""
import asyncio
import logging

from app.celery_app import celery_app

logger = logging.getLogger(__name__)

# DB trigger_type CHECK constraint uses 'festival' but the TriggerEngine
# returns 'calendar'. This map normalises engine output → DB-safe values.
_TRIGGER_TYPE_DB_MAP = {
    "calendar": "festival",
}


def _db_trigger_type(engine_type: str) -> str:
    """Map engine trigger type name to the DB-safe column value."""
    return _TRIGGER_TYPE_DB_MAP.get(engine_type, engine_type)


async def _send_to_elder(elder, message_content: str):
    """Route a proactive message to the correct channel based on elder's user ID.

    - If wechat_user_id ends with @im.wechat → send via iLink
    - Otherwise → send via WeCom API
    """
    user_id = elder.wechat_user_id

    if user_id.endswith("@im.wechat"):
        # iLink channel — retrieve stored context_token
        from app.gateway.ilink_bot import send_message, get_context_token
        context_token = await get_context_token(user_id)
        if context_token:
            await send_message(user_id, message_content, context_token)
            return True
        else:
            logger.warning(
                "No context_token for iLink user %s — cannot send proactive message",
                user_id,
            )
            return False
    else:
        # WeCom channel
        from app.gateway.wecom_api import send_text_message
        await send_text_message(user_id=user_id, content=message_content)
        return True


# ─────────────────────────────────────────────────────────
# Top-level Beat-triggered task: evaluate all elders
# ─────────────────────────────────────────────────────────

@celery_app.task(name="tasks.trigger.evaluate_all_elders")
def evaluate_all_elders():
    """Fan-out: queue per-elder evaluation for all active elders.

    Triggered every 15 minutes by Celery Beat.
    Each elder is evaluated independently as a separate task so a
    slow PKE query or weather API call for one elder does not block others.
    """
    from app.database import sync_session_factory
    from app.models.elder import Elder
    from sqlalchemy import select

    with sync_session_factory() as session:
        stmt = select(Elder).where(Elder.status == "active")
        elders = session.execute(stmt).scalars().all()

    logger.info("Trigger evaluation: queuing %d active elders", len(elders))

    for elder in elders:
        try:
            evaluate_triggers.delay(str(elder.id), elder.wechat_user_id)
        except Exception as e:
            logger.error("Failed to queue trigger eval for elder %s: %s", elder.id, e)


# ─────────────────────────────────────────────────────────
# Per-elder evaluation task
# ─────────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="tasks.trigger.evaluate",
    queue="high_priority",
    max_retries=2,
    default_retry_delay=60,
)
def evaluate_triggers(self, elder_id: str, wechat_user_id: str):
    """Evaluate all trigger conditions for a single elder.

    If a trigger fires and frequency limits allow, queues send_proactive_message.
    """
    try:
        asyncio.run(_evaluate_async(elder_id, wechat_user_id))
    except Exception as e:
        logger.error("evaluate_triggers failed for elder %s: %s", elder_id, e)
        raise self.retry(exc=e)


async def _evaluate_async(elder_id: str, wechat_user_id: str) -> None:
    """Async core of per-elder trigger evaluation."""
    from app.database import async_session_factory
    from app.services.trigger_engine import trigger_engine
    from app.pke.pke_service import pke_service

    async with async_session_factory() as session:
        result = await trigger_engine.evaluate_all(session, elder_id)

        if result is None:
            # No trigger fired (frequency limited or no conditions met)
            return

        trigger_type, trigger_context = result

        # Generate a contextual proactive message
        # Use PKE memory + trigger context as the generation seed
        try:
            memory_ctx = await pke_service.query(elder_id, trigger_context[:100])
        except Exception:
            memory_ctx = ""

        message = await _generate_proactive_message(
            elder_id=elder_id,
            trigger_type=trigger_type,
            trigger_context=trigger_context,
            memory_context=memory_ctx,
        )

        # Queue the send task
        send_proactive_message.delay(
            elder_id=elder_id,
            wechat_user_id=wechat_user_id,
            trigger_type=trigger_type,
            trigger_context=trigger_context,
            content=message,
        )

        logger.info(
            "Elder %s: %s trigger → queued send (%.60s...)",
            elder_id,
            trigger_type,
            message,
        )


async def _generate_proactive_message(
    elder_id: str,
    trigger_type: str,
    trigger_context: str,
    memory_context: str,
) -> str:
    """Generate a natural proactive message given the trigger context."""
    from app.utils.llm import chat_completion
    from datetime import datetime

    now = datetime.now()
    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    date_str = now.strftime("%Y年%m月%d日") + f"（{weekday_names[now.weekday()]}）"

    # Build a trigger-type-specific instruction
    trigger_instructions = {
        "calendar": f"今天有个特别的日子：{trigger_context}。请用这个为话题，自然地问候老人。",
        "weather": f"天气情况：{trigger_context}。请关心老人的出行安全或注意保暖。",
        "memory": f"你记得之前聊过：{trigger_context[:150]}。请自然地跟进一下。",
        "time_gap": "老人已经好一段时间没消息了，请温柔地关心一下他们今天怎么样。",
    }
    instruction = trigger_instructions.get(trigger_type, f"请主动关心一下老人，背景：{trigger_context[:100]}")

    memory_section = ""
    if memory_context and memory_context.strip():
        memory_section = f"\n你记得关于这位老人的信息：\n{memory_context}"

    system_prompt = f"""你是小伴，一位温暖、耐心的AI陪伴助手，专门陪伴60-75岁的居家老人。

性格特点：
- 温和亲切，像老朋友一样说话，不用敬语
- 用简单易懂的语言，避免专业术语
- 善于倾听，记得老人说过的事情
- 关心对方的日常生活、身体状况和心情
- 适当使用语气词（嗯、呢、呀、哦）让对话更自然
- 回复简洁，通常2-4句话，不要长篇大论

今天是{date_str}。{memory_section}"""

    user_prompt = f"（系统指令：{instruction}不要超过3句话，要自然，不要显得像群发消息。）"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        return await chat_completion(messages=messages)
    except Exception as e:
        logger.error("Proactive message generation failed for elder %s: %s", elder_id, e)
        # Safe fallback messages by trigger type
        fallbacks = {
            "calendar": "今天是个好日子，你还好吗？",
            "weather": "最近天气变化大，你注意保暖哦。",
            "memory": "最近怎么样，一切都好吧？",
            "time_gap": "好久没消息了，你还好吧，最近忙什么呢？",
        }
        return fallbacks.get(trigger_type, "最近怎么样，你还好吧？")


# ─────────────────────────────────────────────────────────
# Send task: deliver the proactive message + log result
# ─────────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="tasks.trigger.send",
    queue="high_priority",
    max_retries=3,
    default_retry_delay=30,
)
def send_proactive_message(
    self,
    elder_id: str,
    wechat_user_id: str,
    trigger_type: str,
    trigger_context: str,
    content: str,
):
    """Deliver a proactive message to an elder via WeCom and log the result.

    On success: logs TriggerLog(status=sent) and increments TriggerState count.
    On failure: logs TriggerLog(status=failed) and retries up to max_retries.
    """
    try:
        asyncio.run(_send_async(elder_id, wechat_user_id, trigger_type, trigger_context, content))
    except Exception as e:
        logger.error(
            "send_proactive_message failed for elder %s trigger %s: %s",
            elder_id, trigger_type, e,
        )
        raise self.retry(exc=e)


async def _send_async(
    elder_id: str,
    wechat_user_id: str,
    trigger_type: str,
    trigger_context: str,
    content: str,
) -> None:
    """Async core of proactive message delivery."""
    from types import SimpleNamespace
    from sqlalchemy import select
    from app.database import async_session_factory
    from app.models.elder import Elder
    from app.services.trigger_engine import trigger_engine

    wecom_msg_id = None
    status = "failed"
    skip_reason = None

    try:
        # Resolve elder for channel routing (iLink vs WeCom)
        async with async_session_factory() as lookup_session:
            elder = (
                await lookup_session.execute(
                    select(Elder).where(Elder.wechat_user_id == wechat_user_id)
                )
            ).scalar_one_or_none()
        if elder is None:
            # Fallback: minimal object so routing still works on wechat_user_id
            elder = SimpleNamespace(wechat_user_id=wechat_user_id)

        sent = await _send_to_elder(elder, content)
        if sent:
            status = "sent"
            logger.info(
                "Proactive message sent to elder %s (type=%s, channel=%s)",
                elder_id,
                trigger_type,
                "ilink" if wechat_user_id.endswith("@im.wechat") else "wecom",
            )
        else:
            skip_reason = "delivery skipped (e.g. missing iLink context_token)"
            logger.error(
                "Failed to send proactive message to elder %s: %s",
                elder_id, skip_reason,
            )
    except Exception as e:
        skip_reason = str(e)[:256]
        logger.error(
            "Failed to send proactive message to elder %s: %s",
            elder_id, e,
        )

    # Always log the attempt (map trigger_type to DB-safe value)
    db_type = _db_trigger_type(trigger_type)

    async with async_session_factory() as session:
        await trigger_engine.record_trigger(
            db=session,
            elder_id=elder_id,
            trigger_type=db_type,
            reason=trigger_context[:500] if trigger_context else None,
            status=status,
            message_content=content,
            message_id=wecom_msg_id,
            skip_reason=skip_reason,
        )
        await session.commit()

    if status == "failed":
        raise RuntimeError(f"WeCom send failed: {skip_reason}")


# ─────────────────────────────────────────────────────────
# Midnight reset task
# ─────────────────────────────────────────────────────────

@celery_app.task(name="tasks.trigger.reset_daily_trigger_counts")
def reset_daily_trigger_counts():
    """Reset today_trigger_count for all elders at midnight.

    Triggered by Celery Beat at 00:00 daily.
    Uses eager reset (bulk update) rather than per-elder lazy reset.
    """
    from app.database import sync_session_factory
    from app.models.trigger import TriggerState
    from sqlalchemy import update
    from datetime import date

    today = date.today()

    with sync_session_factory() as session:
        stmt = (
            update(TriggerState)
            .where(TriggerState.today_date != today)
            .values(today_trigger_count=0, today_date=today)
        )
        result = session.execute(stmt)
        session.commit()
        logger.info(
            "Daily trigger count reset: updated %d elder state rows",
            result.rowcount,
        )
