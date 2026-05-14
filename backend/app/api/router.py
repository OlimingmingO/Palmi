"""Main API router — includes all sub-routers."""
from fastapi import APIRouter

from app.api.wechat import router as wechat_router
from app.api.configurator import router as configurator_router
from app.api.admin import router as admin_router

api_router = APIRouter()
api_router.include_router(wechat_router, prefix="/wechat", tags=["WeChat"])
api_router.include_router(configurator_router, prefix="/configurator", tags=["Configurator"])
api_router.include_router(admin_router, prefix="/admin", tags=["Admin"])
