"""tasks.unmet.* — Unmet needs detection tasks."""
import json
import logging
from datetime import datetime, timedelta

from openai import OpenAI
from sqlalchemy import select, and_

from app.celery_app import celery_app
from app.config import settings
from app.database import sync_session_factory as SessionLocal  # sync session for Celery tasks
from app.models.unmet_need import UnmetNeed

logger = logging.getLogger(__name__)

# Use same LLM client pattern as tags.py
client = OpenAI(
    api_key=settings.LLM_PRIMARY_API_KEY,
    base_url=settings.LLM_PRIMARY_BASE_URL,
)

DETECTION_PROMPT = """分析以下对话，判断用户是否有一个未被满足的需求。

未满足需求的定义：用户表达了明确的任务请求或需求意图，但小伴的回复表明未能执行该任务。

判断依据：
- 小伴回复中明确表示帮不了
- 小伴转移话题未解决用户的请求
- 小伴提供了信息但未实际执行任务
- 用户主动放弃（"算了没事"）也算未满足

注意：
- 随口感叹（"要是能帮我买菜就好了"）不算明确请求
- 闲聊、情感倾诉、信息查询成功回答的不算未满足
- 日常寒暄不算

用户消息：{user_message}
小伴回复：{bot_reply}

请以JSON格式回复：
"is_unmet": true/false, "description": "需求描述（如果有）", "category": "需求类别（如：购物类、打车类、就医类、缴费类、联系家人类、其他服务类）", "confidence": 0.0-1.0

只返回JSON，不要其他内容。"""


@celery_app.task(bind=True, name="tasks.unmet.detect", queue="default", max_retries=2)
def detect_unmet_need(self, elder_id: str, conversation_id: str, user_message: str, bot_reply: str):
    """Detect if a conversation exchange contains an unmet need."""
    try:
        prompt = DETECTION_PROMPT.format(user_message=user_message, bot_reply=bot_reply)

        response = client.chat.completions.create(
            model=settings.LLM_PRIMARY_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=200,
        )

        raw = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

        result = json.loads(raw)

        if not result.get("is_unmet", False):
            logger.info("No unmet need detected for conversation %s", conversation_id)
            return

        # Deduplication: check if same elder + category exists in last 7 days
        with SessionLocal() as db:
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            existing = db.execute(
                select(UnmetNeed).where(
                    and_(
                        UnmetNeed.elder_id == elder_id,
                        UnmetNeed.need_category == result["category"],
                        UnmetNeed.created_at >= seven_days_ago,
                        UnmetNeed.is_dismissed == False,
                    )
                )
            ).scalars().first()

            if existing:
                # Increment count
                existing.occurrence_count += 1
                existing.updated_at = datetime.utcnow()
                logger.info(
                    "Incremented unmet need count for %s/%s to %d",
                    elder_id,
                    result["category"],
                    existing.occurrence_count,
                )
            else:
                # Create new
                need = UnmetNeed(
                    elder_id=elder_id,
                    conversation_id=conversation_id,
                    need_description=result.get("description", ""),
                    need_category=result.get("category", "其他服务类"),
                    confidence=result.get("confidence", 0.8),
                )
                db.add(need)
                logger.info("New unmet need: %s for elder %s", result["category"], elder_id)

            db.commit()

    except json.JSONDecodeError as e:
        logger.warning("Failed to parse unmet need LLM response: %s", e)
    except Exception as exc:
        logger.error("Unmet need detection failed: %s", exc)
        raise self.retry(exc=exc, countdown=30)
