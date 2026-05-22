"""Operations backend API endpoints.

All endpoints are mounted under /api/admin/* and protected by HTTP Basic Auth.

Endpoints:
- GET    /elders                         — List elders with status classification
- GET    /elders/{elder_id}              — Tenant detail page aggregated stats
- GET    /elders/{elder_id}/conversations — Date-grouped conversation browser
- GET    /conversations/search           — Full-text search across messages
- GET    /tags/review                    — Low-confidence tag review queue
- PATCH  /tags/{tag_id}                  — Manually correct a message tag
- GET    /unmet-needs                    — Aggregated unmet needs (drill-down via ?category=)
- PATCH  /unmet-needs/{id}/dismiss       — Mark unmet need as false positive
- GET    /stats/dashboard                — Overview dashboard metrics
- GET    /pke/{elder_id}/status          — PKE vault file counts
"""
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from sqlalchemy import and_, cast, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import Date as SqlDate

from app.config import settings
from app.database import get_db
from app.models.conversation import Conversation
from app.models.elder import Elder
from app.models.elder_profile import ElderProfile
from app.models.tag import IntentTag, MessageTag, TagCorrection
from app.models.trigger import TriggerLog
from app.models.unmet_need import UnmetNeed


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

security = HTTPBasic()


def verify_ops_auth(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """HTTP Basic Auth dependency for ops console endpoints."""
    correct_username = secrets.compare_digest(
        credentials.username.encode("utf8"),
        settings.OPS_AUTH_USER.encode("utf8"),
    )
    correct_password = secrets.compare_digest(
        credentials.password.encode("utf8"),
        settings.OPS_AUTH_PASS.encode("utf8"),
    )
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


router = APIRouter(dependencies=[Depends(verify_ops_auth)])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _classify_status(
    last_message_at: Optional[datetime],
    elder_created_at: datetime,
    now: datetime,
) -> str:
    """Classify an elder's engagement status."""
    if last_message_at is None:
        if (now - elder_created_at) < timedelta(days=3):
            return "new"
        return "at_risk"
    delta = now - last_message_at
    if delta < timedelta(days=3):
        return "active"
    if delta < timedelta(days=7):
        return "silent"
    return "at_risk"


_STATUS_PRIORITY = {"at_risk": 0, "silent": 1, "new": 2, "active": 3}


def _status_sort_key(s: str) -> int:
    return _STATUS_PRIORITY.get(s, 99)


def _uuid_str(value) -> Optional[str]:
    if value is None:
        return None
    return str(value)


# ---------------------------------------------------------------------------
# /elders
# ---------------------------------------------------------------------------

@router.get("/elders")
async def list_elders(db: AsyncSession = Depends(get_db)):
    """List all elders with aggregated message stats and status classification."""
    now = _now_utc()
    week_ago = now - timedelta(days=7)

    elders_rows = (await db.execute(select(Elder))).scalars().all()

    # Per-elder stats — total + last_message_at
    totals_stmt = (
        select(
            Conversation.elder_id,
            func.count(Conversation.id).label("total"),
            func.max(Conversation.created_at).label("last_at"),
        )
        .group_by(Conversation.elder_id)
    )
    totals_map = {
        row.elder_id: (row.total, row.last_at)
        for row in (await db.execute(totals_stmt)).all()
    }

    # Per-elder weekly message count
    weekly_stmt = (
        select(
            Conversation.elder_id,
            func.count(Conversation.id).label("weekly"),
        )
        .where(Conversation.created_at >= week_ago)
        .group_by(Conversation.elder_id)
    )
    weekly_map = {
        row.elder_id: row.weekly
        for row in (await db.execute(weekly_stmt)).all()
    }

    items = []
    for elder in elders_rows:
        total, last_at = totals_map.get(elder.id, (0, None))
        weekly = weekly_map.get(elder.id, 0)
        engagement = _classify_status(last_at, elder.created_at, now)
        items.append({
            "id": _uuid_str(elder.id),
            "nickname": elder.nickname,
            "wechat_user_id": elder.wechat_user_id,
            "phone": elder.phone,
            "status": elder.status,
            "engagement_status": engagement,
            "total_messages": int(total or 0),
            "weekly_messages": int(weekly or 0),
            "last_message_at": last_at.isoformat() if last_at else None,
            "created_at": elder.created_at.isoformat() if elder.created_at else None,
        })

    items.sort(key=lambda x: (_status_sort_key(x["engagement_status"]), x["nickname"] or ""))
    return {"items": items, "total": len(items)}


# ---------------------------------------------------------------------------
# /elders/{elder_id}
# ---------------------------------------------------------------------------

@router.get("/elders/{elder_id}")
async def get_elder_detail(elder_id: str, db: AsyncSession = Depends(get_db)):
    """Tenant detail page (F10) — basic info + aggregated stats."""
    try:
        elder_uuid = uuid.UUID(elder_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid elder_id format")

    elder = (await db.execute(select(Elder).where(Elder.id == elder_uuid))).scalar_one_or_none()
    if elder is None:
        raise HTTPException(status_code=404, detail="Elder not found")

    now = _now_utc()
    week_ago = now - timedelta(days=7)

    # Conversation stats
    total_messages = (
        await db.execute(
            select(func.count(Conversation.id)).where(Conversation.elder_id == elder_uuid)
        )
    ).scalar_one() or 0

    total_sessions = (
        await db.execute(
            select(func.count(distinct(cast(Conversation.created_at, SqlDate))))
            .where(Conversation.elder_id == elder_uuid)
        )
    ).scalar_one() or 0

    weekly_messages = (
        await db.execute(
            select(func.count(Conversation.id)).where(
                and_(
                    Conversation.elder_id == elder_uuid,
                    Conversation.created_at >= week_ago,
                )
            )
        )
    ).scalar_one() or 0

    avg_daily_messages = (
        float(total_messages) / float(total_sessions) if total_sessions else 0.0
    )

    recent_rows = (
        await db.execute(
            select(Conversation)
            .where(Conversation.elder_id == elder_uuid)
            .order_by(Conversation.created_at.desc())
            .limit(5)
        )
    ).scalars().all()
    recent_messages = [
        {
            "id": _uuid_str(r.id),
            "role": r.role,
            "preview": (r.content or "")[:20],
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in recent_rows
    ]

    # Tag distribution
    tag_dist_rows = (
        await db.execute(
            select(IntentTag.name, func.count(MessageTag.id))
            .join(IntentTag, IntentTag.id == MessageTag.tag_id)
            .where(MessageTag.elder_id == elder_uuid)
            .group_by(IntentTag.name)
        )
    ).all()
    tag_distribution = {name: int(cnt) for name, cnt in tag_dist_rows}

    # Trigger history (last 20)
    trigger_rows = (
        await db.execute(
            select(TriggerLog)
            .where(TriggerLog.elder_id == elder_uuid)
            .order_by(TriggerLog.created_at.desc())
            .limit(20)
        )
    ).scalars().all()
    trigger_history = [
        {
            "id": _uuid_str(t.id),
            "trigger_type": t.trigger_type,
            "reason": t.reason,
            "status": t.status,
            "skip_reason": t.skip_reason,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in trigger_rows
    ]

    # PKE vault status — filesystem
    pke_status = _read_pke_status(elder_id)

    # Latest config (elder_profile) version
    latest_profile = (
        await db.execute(
            select(ElderProfile)
            .where(ElderProfile.elder_id == elder_uuid)
            .order_by(ElderProfile.version.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    config_status = (
        {
            "version": latest_profile.version,
            "last_updated_by": latest_profile.last_updated_by,
            "updated_at": latest_profile.updated_at.isoformat() if latest_profile.updated_at else None,
        }
        if latest_profile
        else None
    )

    last_message_at = recent_rows[0].created_at if recent_rows else None

    return {
        "id": _uuid_str(elder.id),
        "nickname": elder.nickname,
        "wechat_user_id": elder.wechat_user_id,
        "phone": elder.phone,
        "status": elder.status,
        "engagement_status": _classify_status(last_message_at, elder.created_at, now),
        "created_at": elder.created_at.isoformat() if elder.created_at else None,
        "conversation_stats": {
            "total_messages": int(total_messages),
            "total_sessions": int(total_sessions),
            "weekly_messages": int(weekly_messages),
            "avg_daily_messages": round(avg_daily_messages, 2),
            "recent_messages": recent_messages,
        },
        "tag_distribution": tag_distribution,
        "trigger_history": trigger_history,
        "pke_status": pke_status,
        "config_status": config_status,
    }


# ---------------------------------------------------------------------------
# /elders/{elder_id}/conversations
# ---------------------------------------------------------------------------

@router.get("/elders/{elder_id}/conversations")
async def get_elder_conversations(
    elder_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    date: Optional[str] = Query(None, description="YYYY-MM-DD — return all messages for this date"),
    db: AsyncSession = Depends(get_db),
):
    """Date-grouped conversation browser (F2)."""
    try:
        elder_uuid = uuid.UUID(elder_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid elder_id format")

    elder = (await db.execute(select(Elder).where(Elder.id == elder_uuid))).scalar_one_or_none()
    if elder is None:
        raise HTTPException(status_code=404, detail="Elder not found")

    # Specific date — return all messages for that date in chronological order
    if date:
        try:
            target_day = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format, expected YYYY-MM-DD")

        day_col = cast(Conversation.created_at, SqlDate)
        msg_rows = (
            await db.execute(
                select(Conversation)
                .where(
                    and_(
                        Conversation.elder_id == elder_uuid,
                        day_col == target_day,
                    )
                )
                .order_by(Conversation.created_at.asc())
            )
        ).scalars().all()

        return {
            "elder_id": elder_id,
            "date": date,
            "messages": [
                {
                    "id": _uuid_str(m.id),
                    "role": m.role,
                    "content": m.content,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in msg_rows
            ],
            "total": len(msg_rows),
        }

    # Default: grouped by date, paginated
    day_col = cast(Conversation.created_at, SqlDate).label("day")
    grouped_stmt = (
        select(
            day_col,
            func.count(Conversation.id).label("msg_count"),
            func.min(Conversation.created_at).label("first_at"),
        )
        .where(Conversation.elder_id == elder_uuid)
        .group_by(day_col)
        .order_by(day_col.desc())
    )

    all_groups = (await db.execute(grouped_stmt)).all()
    total = len(all_groups)
    offset = (page - 1) * page_size
    page_groups = all_groups[offset : offset + page_size]

    items = []
    for grp in page_groups:
        first_msg = (
            await db.execute(
                select(Conversation.content)
                .where(
                    and_(
                        Conversation.elder_id == elder_uuid,
                        cast(Conversation.created_at, SqlDate) == grp.day,
                    )
                )
                .order_by(Conversation.created_at.asc())
                .limit(1)
            )
        ).scalar_one_or_none()
        items.append({
            "date": grp.day.isoformat() if grp.day else None,
            "message_count": int(grp.msg_count),
            "preview": (first_msg or "")[:20],
        })

    return {
        "elder_id": elder_id,
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
    }


# ---------------------------------------------------------------------------
# /conversations/search
# ---------------------------------------------------------------------------

@router.get("/conversations/search")
async def search_conversations(
    q: str = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Full-text search across all conversation messages (SQL ILIKE for MVP)."""
    if not q or not q.strip():
        return {"items": [], "total": 0}
    pattern = f"%{q}%"
    offset = (page - 1) * page_size

    total = (
        await db.execute(
            select(func.count(Conversation.id)).where(Conversation.content.ilike(pattern))
        )
    ).scalar_one() or 0

    rows = (
        await db.execute(
            select(
                Conversation.id,
                Conversation.elder_id,
                Conversation.role,
                Conversation.content,
                Conversation.created_at,
                Elder.nickname,
            )
            .join(Elder, Elder.id == Conversation.elder_id)
            .where(Conversation.content.ilike(pattern))
            .order_by(Conversation.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
    ).all()

    items = [
        {
            "id": _uuid_str(row.id),
            "elder_id": _uuid_str(row.elder_id),
            "elder_nickname": row.nickname,
            "role": row.role,
            "content": row.content,
            "match": q,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]

    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": int(total),
        "query": q,
    }


# ---------------------------------------------------------------------------
# /tags/review
# ---------------------------------------------------------------------------

@router.get("/tags/review")
async def list_tag_review_queue(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Low-confidence tags queue (F4) — confidence < 0.6."""
    offset = (page - 1) * page_size

    total = (
        await db.execute(
            select(func.count(MessageTag.id)).where(MessageTag.confidence < 0.6)
        )
    ).scalar_one() or 0

    rows = (
        await db.execute(
            select(
                MessageTag.id,
                MessageTag.message_id,
                MessageTag.elder_id,
                MessageTag.tag_id,
                MessageTag.confidence,
                MessageTag.source,
                MessageTag.created_at,
                IntentTag.name.label("tag_name"),
                Conversation.content.label("message_content"),
                Conversation.role.label("message_role"),
                Elder.nickname.label("elder_nickname"),
            )
            .join(IntentTag, IntentTag.id == MessageTag.tag_id)
            .join(Conversation, Conversation.id == MessageTag.message_id)
            .join(Elder, Elder.id == MessageTag.elder_id)
            .where(MessageTag.confidence < 0.6)
            .order_by(MessageTag.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
    ).all()

    items = [
        {
            "id": _uuid_str(r.id),
            "message_id": _uuid_str(r.message_id),
            "elder_id": _uuid_str(r.elder_id),
            "elder_nickname": r.elder_nickname,
            "tag_id": r.tag_id,
            "tag_name": r.tag_name,
            "confidence": float(r.confidence),
            "source": r.source,
            "message_content": r.message_content,
            "message_role": r.message_role,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]

    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": int(total),
    }


# ---------------------------------------------------------------------------
# PATCH /tags/{tag_id}
# ---------------------------------------------------------------------------

class TagCorrectRequest(BaseModel):
    new_tag: str


@router.patch("/tags/{tag_id}")
async def correct_tag(
    tag_id: str,
    body: TagCorrectRequest,
    db: AsyncSession = Depends(get_db),
    operator: str = Depends(verify_ops_auth),
):
    """Manually correct a message tag and log a TagCorrection audit row."""
    try:
        mt_uuid = uuid.UUID(tag_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tag_id format")

    message_tag = (
        await db.execute(select(MessageTag).where(MessageTag.id == mt_uuid))
    ).scalar_one_or_none()
    if message_tag is None:
        raise HTTPException(status_code=404, detail="MessageTag not found")

    new_tag = (
        await db.execute(select(IntentTag).where(IntentTag.name == body.new_tag))
    ).scalar_one_or_none()
    if new_tag is None:
        raise HTTPException(status_code=404, detail=f"Intent tag '{body.new_tag}' not found")

    original_tag_id = message_tag.tag_id
    message_tag.tag_id = new_tag.id
    message_tag.source = "manual"
    message_tag.confidence = 1.0
    message_tag.needs_review = False

    correction = TagCorrection(
        message_tag_id=message_tag.id,
        original_tag_id=original_tag_id,
        corrected_tag_id=new_tag.id,
        reason=f"Corrected by ops user '{operator}'",
    )
    db.add(correction)
    await db.flush()

    return {
        "id": _uuid_str(message_tag.id),
        "message_id": _uuid_str(message_tag.message_id),
        "tag_id": message_tag.tag_id,
        "tag_name": new_tag.name,
        "source": message_tag.source,
        "confidence": float(message_tag.confidence),
        "correction_id": _uuid_str(correction.id),
    }


# ---------------------------------------------------------------------------
# /unmet-needs
# ---------------------------------------------------------------------------

@router.get("/unmet-needs")
async def list_unmet_needs(
    category: Optional[str] = Query(None, description="Drill-down: return individual rows for this category"),
    db: AsyncSession = Depends(get_db),
):
    """Aggregated unmet needs (F7). Use ?category=... to drill into individual rows."""
    if category:
        rows = (
            await db.execute(
                select(
                    UnmetNeed.id,
                    UnmetNeed.elder_id,
                    UnmetNeed.conversation_id,
                    UnmetNeed.need_description,
                    UnmetNeed.need_category,
                    UnmetNeed.confidence,
                    UnmetNeed.occurrence_count,
                    UnmetNeed.is_dismissed,
                    UnmetNeed.created_at,
                    UnmetNeed.updated_at,
                    Elder.nickname.label("elder_nickname"),
                )
                .join(Elder, Elder.id == UnmetNeed.elder_id)
                .where(
                    and_(
                        UnmetNeed.is_dismissed.is_(False),
                        UnmetNeed.need_category == category,
                    )
                )
                .order_by(UnmetNeed.occurrence_count.desc(), UnmetNeed.created_at.desc())
            )
        ).all()
        items = [
            {
                "id": _uuid_str(r.id),
                "elder_id": _uuid_str(r.elder_id),
                "elder_nickname": r.elder_nickname,
                "conversation_id": _uuid_str(r.conversation_id),
                "need_description": r.need_description,
                "need_category": r.need_category,
                "confidence": float(r.confidence),
                "occurrence_count": int(r.occurrence_count),
                "is_dismissed": bool(r.is_dismissed),
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in rows
        ]
        return {"category": category, "items": items, "total": len(items)}

    # Aggregated view — group by category
    agg_rows = (
        await db.execute(
            select(
                UnmetNeed.need_category,
                func.sum(UnmetNeed.occurrence_count).label("total_occurrences"),
                func.count(distinct(UnmetNeed.elder_id)).label("elder_count"),
            )
            .where(UnmetNeed.is_dismissed.is_(False))
            .group_by(UnmetNeed.need_category)
            .order_by(func.sum(UnmetNeed.occurrence_count).desc())
        )
    ).all()

    items = []
    for row in agg_rows:
        # Fetch elder names for this category
        nick_rows = (
            await db.execute(
                select(distinct(Elder.nickname))
                .join(UnmetNeed, UnmetNeed.elder_id == Elder.id)
                .where(
                    and_(
                        UnmetNeed.is_dismissed.is_(False),
                        UnmetNeed.need_category == row.need_category,
                    )
                )
            )
        ).all()
        nicknames = [n[0] for n in nick_rows if n[0]]
        items.append({
            "need_category": row.need_category,
            "total_occurrences": int(row.total_occurrences or 0),
            "elder_count": int(row.elder_count or 0),
            "elder_nicknames": nicknames,
        })

    return {"items": items, "total": len(items)}


# ---------------------------------------------------------------------------
# PATCH /unmet-needs/{id}/dismiss
# ---------------------------------------------------------------------------

@router.patch("/unmet-needs/{need_id}/dismiss")
async def dismiss_unmet_need(need_id: str, db: AsyncSession = Depends(get_db)):
    """Mark an unmet need as false positive."""
    try:
        need_uuid = uuid.UUID(need_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid need_id format")

    need = (
        await db.execute(select(UnmetNeed).where(UnmetNeed.id == need_uuid))
    ).scalar_one_or_none()
    if need is None:
        raise HTTPException(status_code=404, detail="UnmetNeed not found")

    need.is_dismissed = True
    await db.flush()
    return {"id": _uuid_str(need.id), "is_dismissed": True}


# ---------------------------------------------------------------------------
# /stats/dashboard
# ---------------------------------------------------------------------------

@router.get("/stats/dashboard")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Overview metrics for the ops dashboard home page."""
    now = _now_utc()
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    week_ago = now - timedelta(days=7)

    total_users = (
        await db.execute(select(func.count(Elder.id)))
    ).scalar_one() or 0

    dau = (
        await db.execute(
            select(func.count(distinct(Conversation.elder_id)))
            .where(Conversation.created_at >= today_start)
        )
    ).scalar_one() or 0

    wau = (
        await db.execute(
            select(func.count(distinct(Conversation.elder_id)))
            .where(Conversation.created_at >= week_ago)
        )
    ).scalar_one() or 0

    total_messages = (
        await db.execute(select(func.count(Conversation.id)))
    ).scalar_one() or 0

    # Status classification — reuse logic from /elders
    elders_rows = (await db.execute(select(Elder))).scalars().all()
    totals_stmt = (
        select(
            Conversation.elder_id,
            func.max(Conversation.created_at).label("last_at"),
        )
        .group_by(Conversation.elder_id)
    )
    last_at_map = {
        row.elder_id: row.last_at
        for row in (await db.execute(totals_stmt)).all()
    }

    active_count = silent_count = at_risk_count = new_count = 0
    for elder in elders_rows:
        status_val = _classify_status(last_at_map.get(elder.id), elder.created_at, now)
        if status_val == "active":
            active_count += 1
        elif status_val == "silent":
            silent_count += 1
        elif status_val == "at_risk":
            at_risk_count += 1
        elif status_val == "new":
            new_count += 1

    # avg_session_depth — messages per (elder, day) averaged across all (elder, day) pairs
    day_col = cast(Conversation.created_at, SqlDate)
    session_counts = (
        await db.execute(
            select(func.count(Conversation.id))
            .group_by(Conversation.elder_id, day_col)
        )
    ).scalars().all()
    avg_session_depth = (
        sum(session_counts) / len(session_counts) if session_counts else 0.0
    )

    return {
        "total_users": int(total_users),
        "dau": int(dau),
        "wau": int(wau),
        "total_messages": int(total_messages),
        "active_count": active_count,
        "silent_count": silent_count,
        "at_risk_count": at_risk_count,
        "new_count": new_count,
        "avg_session_depth": round(float(avg_session_depth), 2),
    }


# ---------------------------------------------------------------------------
# /pke/{elder_id}/status
# ---------------------------------------------------------------------------

def _read_pke_status(elder_id: str) -> dict:
    """Read filesystem to count PKE vault files for an elder. Handles missing dirs."""
    base = os.path.join(settings.PKE_VAULT_ROOT, str(elder_id))
    result = {
        "raw_file_count": 0,
        "wiki_file_count": 0,
        "raw_last_modified": None,
        "wiki_last_modified": None,
        "vault_path": base,
    }

    for kind in ("raw", "wiki"):
        dir_path = os.path.join(base, kind)
        if not os.path.isdir(dir_path):
            continue
        try:
            names = [n for n in os.listdir(dir_path) if not n.startswith(".")]
        except OSError:
            continue
        files = [os.path.join(dir_path, n) for n in names if os.path.isfile(os.path.join(dir_path, n))]
        result[f"{kind}_file_count"] = len(files)
        if files:
            try:
                latest = max(os.path.getmtime(p) for p in files)
                result[f"{kind}_last_modified"] = datetime.fromtimestamp(
                    latest, tz=timezone.utc
                ).isoformat()
            except OSError:
                pass
    return result


@router.get("/pke/{elder_id}/status")
async def get_pke_status(elder_id: str, db: AsyncSession = Depends(get_db)):
    """PKE vault file counts and latest modification times."""
    try:
        elder_uuid = uuid.UUID(elder_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid elder_id format")

    elder = (await db.execute(select(Elder).where(Elder.id == elder_uuid))).scalar_one_or_none()
    if elder is None:
        raise HTTPException(status_code=404, detail="Elder not found")

    return _read_pke_status(elder_id)
