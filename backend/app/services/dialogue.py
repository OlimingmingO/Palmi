"""Dialogue service — manages conversation and LLM interaction.

Phase 1: Persona system prompt, DB-backed context, PKE memory injection.
"""
import logging
from datetime import datetime
from typing import Optional

from app.utils.llm import chat_completion

logger = logging.getLogger(__name__)

MAX_CONTEXT_MESSAGES = 10

XIAO_BAN_SYSTEM_PROMPT = """你是小伴，一位温暖、耐心的AI陪伴助手，专门陪伴60-75岁的居家老人。

性格特点：
- 温和亲切，像老朋友一样说话，不用敬语
- 用简单易懂的语言，避免专业术语
- 善于倾听，记得老人说过的事情
- 关心对方的日常生活、身体状况和心情
- 适当使用语气词（嗯、呢、呀、哦）让对话更自然
- 回复简洁，通常2-4句话，不要长篇大论
- 遇到紧急情况（如跌倒、身体不适）立即建议联系家人或拨打120

今天是{date}。

{memory_context}"""


def _build_system_prompt(memory_context: str = "") -> str:
    """Build the system prompt with current date and memory context."""
    now = datetime.now()
    date_str = now.strftime("%Y年%m月%d日 %H:%M")
    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    date_str += f"（{weekday_names[now.weekday()]}）"

    memory_section = ""
    if memory_context.strip():
        memory_section = f"\n你记得关于这位老人的信息：\n{memory_context}"

    return XIAO_BAN_SYSTEM_PROMPT.format(
        date=date_str,
        memory_context=memory_section,
    )


async def get_reply(
    elder_id: str,
    user_message: str,
    history: Optional[list[dict]] = None,
    memory_context: str = "",
) -> str:
    """Process a user message and get an AI reply.

    Args:
        elder_id: UUID string identifying the elder
        user_message: The text message from the user
        history: Previous conversation messages from DB [{role, content}]
        memory_context: PKE memory search results to inject into prompt

    Returns:
        AI assistant reply text
    """
    # Build system prompt with persona + memory
    system_prompt = _build_system_prompt(memory_context)

    # Assemble messages: system + history + current user message
    messages = [{"role": "system", "content": system_prompt}]

    if history:
        # Take last N messages from DB history
        recent = history[-MAX_CONTEXT_MESSAGES:]
        messages.extend(recent)

    messages.append({"role": "user", "content": user_message})

    try:
        reply = await chat_completion(messages=messages)
    except RuntimeError as e:
        logger.error("LLM failed for elder %s: %s", elder_id, str(e))
        reply = "抱歉，我暂时无法回复。请稍后再试。"

    return reply


async def generate_greeting(elder_id: str, memory_context: str = "") -> str:
    """Generate a proactive morning greeting for an elder.

    Uses the persona prompt + any available memory to create
    a natural, personalized greeting.
    """
    system_prompt = _build_system_prompt(memory_context)

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": "（系统指令：现在是早上，请主动跟这位老人打个招呼。自然简短，像老朋友一样，"
            "如果你记得他们说过的事情可以提一句。不要超过2-3句话。）",
        },
    ]

    try:
        reply = await chat_completion(messages=messages)
    except RuntimeError as e:
        logger.error("Greeting generation failed for elder %s: %s", elder_id, str(e))
        reply = "早上好呀！今天感觉怎么样？"

    return reply
