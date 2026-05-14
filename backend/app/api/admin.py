"""Operations backend API endpoints.

Handles:
- /api/admin/conversations — Conversation browsing and search
- /api/admin/tags — Intent tag management
- /api/admin/unmet — Unmet needs detection results
- /api/admin/stats — Dashboard statistics
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/conversations")
async def list_conversations():
    """Browse conversations with filtering and pagination."""
    # TODO: Implement conversation list with full-text search
    pass


@router.get("/stats/dashboard")
async def get_dashboard_stats():
    """Get overview dashboard statistics."""
    # TODO: Active users, message count, unmet needs count
    pass
