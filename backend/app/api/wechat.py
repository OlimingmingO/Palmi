"""Enterprise WeChat callback and message endpoints.

Handles:
- /api/wechat/callback — WeCom message verification and push
- /api/wechat/event — WeCom event notifications
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/callback")
async def verify_callback():
    """WeCom URL verification (GET request)."""
    # TODO: Implement WeCom signature verification
    pass


@router.post("/callback")
async def receive_message():
    """Receive and process WeCom messages."""
    # TODO: Decrypt message → resolve tenant → route to dialogue service
    pass
