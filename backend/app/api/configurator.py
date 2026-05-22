"""Configurator (family member) Web Console API endpoints.

Mounted at `/api/configurator/...` (see `app/api/router.py`).

Endpoints:
- POST /auth/login                        — Simple password login
- POST /elders                            — Create elder + initial understanding doc
- GET  /elders/{elder_id}                 — Fetch elder + latest profile summary
- POST /elders/{elder_id}/profile         — Append/merge new profile text
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.configurator import Configurator
from app.models.elder import Elder
from app.models.elder_profile import ElderProfile
from app.pke.pke_service import pke_service
from app.services.configurator_service import (
    generate_summary,
    generate_understanding_doc,
    merge_profile_text,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# -------------------------- Auth --------------------------

# For MVP we issue a single static bearer token equal to the configured password.
# Subsequent requests must send it via either:
#   - Header `X-Config-Token: <password>`
#   - Header `Authorization: Bearer <password>`
def _extract_token(x_config_token: Optional[str], authorization: Optional[str]) -> Optional[str]:
    if x_config_token:
        return x_config_token.strip()
    if authorization:
        value = authorization.strip()
        if value.lower().startswith("bearer "):
            return value[7:].strip()
        return value
    return None


async def verify_configurator_auth(
    x_config_token: Optional[str] = Header(default=None, alias="X-Config-Token"),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> None:
    """FastAPI dependency: enforces the shared configurator password.

    Raises 401 if the supplied token does not match settings.CONFIGURATOR_PASSWORD.
    """
    token = _extract_token(x_config_token, authorization)
    if not token or token != settings.CONFIGURATOR_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing configurator credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# -------------------------- Schemas --------------------------


class LoginRequest(BaseModel):
    password: str = Field(..., min_length=1, max_length=128)


class LoginResponse(BaseModel):
    token: str
    message: str


class CreateElderRequest(BaseModel):
    nickname: str = Field(..., min_length=1, max_length=64)
    profile_text: str = Field(..., min_length=1)
    contributor_relationship: str = Field(..., min_length=1, max_length=32)
    contributor_name: str = Field(default="", max_length=64)
    contributor_phone: Optional[str] = Field(default=None, max_length=20)


class CreateElderResponse(BaseModel):
    elder_id: str
    summary: str
    understanding_doc_version: int


class ElderDetailResponse(BaseModel):
    elder_id: str
    nickname: Optional[str]
    status: str
    created_at: str
    profile_version: Optional[int]
    profile_summary: Optional[str]
    profile_content: Optional[str]


class UpdateProfileRequest(BaseModel):
    profile_text: str = Field(..., min_length=1)
    contributor_relationship: str = Field(..., min_length=1, max_length=32)


class UpdateProfileResponse(BaseModel):
    elder_id: str
    summary: str
    understanding_doc_version: int


# -------------------------- Helpers --------------------------


def _write_vault_seed(elder_id: str, understanding_doc: str) -> None:
    """Write the initial understanding doc into the elder's PKE vault as raw seed."""
    try:
        vault_root = Path(pke_service.vault_path(elder_id))
        raw_dir = vault_root / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        seed_path = raw_dir / "initial_profile.md"
        seed_path.write_text(understanding_doc, encoding="utf-8")
        logger.info("Wrote initial profile seed to vault for elder %s", elder_id)
    except Exception as exc:  # pragma: no cover — non-fatal
        logger.warning("Failed to write vault seed for %s: %s", elder_id, exc)


async def _latest_profile(session: AsyncSession, elder_id: uuid.UUID) -> Optional[ElderProfile]:
    stmt = (
        select(ElderProfile)
        .where(ElderProfile.elder_id == elder_id)
        .order_by(ElderProfile.version.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def _parse_elder_id(elder_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(elder_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid elder_id (must be UUID)",
        )


# -------------------------- Endpoints --------------------------


@router.post("/auth/login", response_model=LoginResponse)
async def login(payload: LoginRequest) -> LoginResponse:
    """Validate the shared configurator password and return a bearer token.

    The token is simply the configured password — clients should send it back
    as `X-Config-Token` or `Authorization: Bearer <token>` on subsequent calls.
    """
    if payload.password != settings.CONFIGURATOR_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
        )
    return LoginResponse(token=settings.CONFIGURATOR_PASSWORD, message="Login successful")


@router.post(
    "/elders",
    response_model=CreateElderResponse,
    dependencies=[Depends(verify_configurator_auth)],
)
async def create_elder(
    payload: CreateElderRequest,
    db: AsyncSession = Depends(get_db),
) -> CreateElderResponse:
    """Create a new elder + initial understanding document.

    Steps:
    1. Insert Elder (with placeholder wechat_user_id since not from WeChat yet).
    2. Insert Configurator linked to the elder.
    3. Generate understanding doc + summary via LLM.
    4. Persist ElderProfile (version=1).
    5. Initialize PKE vault and seed it with the understanding doc.
    """
    placeholder_wechat_id = f"web_{uuid.uuid4().hex}"

    elder = Elder(
        wechat_user_id=placeholder_wechat_id,
        nickname=payload.nickname.strip(),
        status="active",
    )
    db.add(elder)
    await db.flush()  # populate elder.id

    configurator = Configurator(
        elder_id=elder.id,
        login_name=f"{placeholder_wechat_id}_{uuid.uuid4().hex[:8]}",
        nickname=payload.contributor_name.strip(),
        relationship=payload.contributor_relationship.strip(),
        phone=(payload.contributor_phone or "").strip() or None,
        is_primary=True,
    )
    db.add(configurator)

    understanding_doc = await generate_understanding_doc(
        raw_text=payload.profile_text,
        contributor_relationship=payload.contributor_relationship,
    )
    summary = await generate_summary(understanding_doc)

    profile = ElderProfile(
        elder_id=elder.id,
        content=understanding_doc,
        version=1,
        last_updated_by="configurator",
    )
    db.add(profile)
    await db.flush()

    elder_id_str = str(elder.id)

    # PKE init and seed are non-fatal — wrap broadly to never break elder creation.
    try:
        pke_service.init_vault(elder_id_str)
    except Exception as exc:  # pragma: no cover — non-fatal
        logger.warning("pke_service.init_vault failed for %s: %s", elder_id_str, exc)

    _write_vault_seed(elder_id_str, understanding_doc)

    return CreateElderResponse(
        elder_id=elder_id_str,
        summary=summary,
        understanding_doc_version=1,
    )


@router.get(
    "/elders/{elder_id}",
    response_model=ElderDetailResponse,
    dependencies=[Depends(verify_configurator_auth)],
)
async def get_elder(
    elder_id: str,
    db: AsyncSession = Depends(get_db),
) -> ElderDetailResponse:
    """Return elder basic info plus the latest profile version + summary."""
    eid = _parse_elder_id(elder_id)
    elder = await db.get(Elder, eid)
    if elder is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Elder not found")

    profile = await _latest_profile(db, eid)
    profile_summary: Optional[str] = None
    profile_content: Optional[str] = None
    profile_version: Optional[int] = None
    if profile is not None:
        profile_content = profile.content
        profile_version = profile.version
        try:
            profile_summary = await generate_summary(profile.content)
        except Exception as exc:  # pragma: no cover — non-fatal
            logger.warning("get_elder summary generation failed for %s: %s", elder_id, exc)
            profile_summary = None

    return ElderDetailResponse(
        elder_id=str(elder.id),
        nickname=elder.nickname,
        status=elder.status,
        created_at=elder.created_at.isoformat() if elder.created_at else "",
        profile_version=profile_version,
        profile_summary=profile_summary,
        profile_content=profile_content,
    )


@router.post(
    "/elders/{elder_id}/profile",
    response_model=UpdateProfileResponse,
    dependencies=[Depends(verify_configurator_auth)],
)
async def append_profile(
    elder_id: str,
    payload: UpdateProfileRequest,
    db: AsyncSession = Depends(get_db),
) -> UpdateProfileResponse:
    """Append/merge new configurator-supplied text into the latest understanding doc.

    Stores the result as a new ElderProfile row with version = previous + 1.
    """
    eid = _parse_elder_id(elder_id)
    elder = await db.get(Elder, eid)
    if elder is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Elder not found")

    existing = await _latest_profile(db, eid)
    existing_doc = existing.content if existing else ""
    next_version = (existing.version + 1) if existing else 1

    merged_doc = await merge_profile_text(
        existing_doc=existing_doc,
        new_text=payload.profile_text,
        contributor_relationship=payload.contributor_relationship,
    )
    summary = await generate_summary(merged_doc)

    new_profile = ElderProfile(
        elder_id=eid,
        content=merged_doc,
        version=next_version,
        last_updated_by="configurator",
    )
    db.add(new_profile)
    await db.flush()

    return UpdateProfileResponse(
        elder_id=str(elder.id),
        summary=summary,
        understanding_doc_version=next_version,
    )
