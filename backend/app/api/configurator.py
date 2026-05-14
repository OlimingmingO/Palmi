"""Configurator (family member) mini-program API endpoints.

Handles:
- /api/configurator/auth — WeChat OAuth login
- /api/configurator/profile — Elder profile initialization and update
- /api/configurator/message — Leave a message for elder
- /api/configurator/alert — Emergency notification settings
"""
from fastapi import APIRouter

router = APIRouter()


@router.post("/auth/login")
async def wechat_login():
    """WeChat mini-program OAuth login."""
    # TODO: Exchange code for openid, create/lookup configurator
    pass


@router.get("/elders")
async def list_linked_elders():
    """List elders linked to this configurator."""
    # TODO: Return elder list with basic status
    pass
