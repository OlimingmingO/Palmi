"""Manual test endpoint — verifies full Phase 1 pipeline without WeCom."""
from fastapi import APIRouter, Query
from app.database import async_session_factory
from app.services import elder_service, conversation_service
from app.services.dialogue import get_reply
from app.pke.pke_service import pke_service

router = APIRouter()


@router.get("/chat")
async def test_chat(
    user_id: str = Query(default="test_user_001"),
    msg: str = Query(default="你是谁"),
):
    """Directly test the Phase 1 pipeline: elder resolution, history, PKE, LLM."""
    async with async_session_factory() as session:
        async with session.begin():
            elder = await elder_service.get_or_create_elder(db=session, wechat_user_id=user_id)
            history = await conversation_service.get_recent(db=session, elder_id=elder.id, limit=10)
            memory_ctx = await pke_service.query(str(elder.id), msg)
            reply = await get_reply(
                elder_id=str(elder.id),
                user_message=msg,
                history=history,
                memory_context=memory_ctx,
            )
            await conversation_service.save_message(db=session, elder_id=elder.id, role="user", content=msg)
            await conversation_service.save_message(db=session, elder_id=elder.id, role="assistant", content=reply)

    return {
        "elder_id": str(elder.id),
        "reply": reply,
        "memory_context": memory_ctx,
        "history_count": len(history),
    }
