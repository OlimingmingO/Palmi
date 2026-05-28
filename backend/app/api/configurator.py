"""Configurator (family member) Web Console API endpoints.

Mounted at `/api/configurator/...` (see `app/api/router.py`).

Endpoints:
- POST /auth/login                        — Login by login_name + shared password, returns JWT
- POST /elders                            — Create elder + initial understanding doc (shared-password gated)
- GET  /elders                            — List elders owned by the authenticated configurator
- GET  /elders/{elder_id}                 — Fetch elder + latest profile summary (ownership-checked)
- POST /elders/{elder_id}/profile         — Append/merge new profile text (ownership-checked)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import jwt
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

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = 7


def _create_jwt(configurator_id: uuid.UUID, elder_id: uuid.UUID) -> str:
    """Sign a JWT carrying the configurator's identity and owned elder."""
    payload = {
        "sub": str(configurator_id),
        "elder_id": str(elder_id),
        "exp": datetime.now(tz=timezone.utc) + timedelta(days=JWT_EXPIRE_DAYS),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=JWT_ALGORITHM)


async def get_current_configurator(
    authorization: str = Header(..., alias="Authorization"),
) -> dict:
    """Extract configurator identity from a JWT Bearer token.

    Returns a dict with `configurator_id` and `elder_id` (both as strings).
    Raises 401 on any decode/format/expiry error.
    """
    try:
        scheme, token = authorization.split(" ", 1)
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid auth scheme",
                headers={"WWW-Authenticate": "Bearer"},
            )
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return {
            "configurator_id": payload["sub"],
            "elder_id": payload["elder_id"],
        }
    except HTTPException:
        raise
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _extract_shared_token(x_config_token: Optional[str], authorization: Optional[str]) -> Optional[str]:
    if x_config_token:
        return x_config_token.strip()
    if authorization:
        value = authorization.strip()
        if value.lower().startswith("bearer "):
            return value[7:].strip()
        return value
    return None


async def verify_shared_password(
    x_config_token: Optional[str] = Header(default=None, alias="X-Config-Token"),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> None:
    """FastAPI dependency that enforces the shared configurator password.

    Used only by the elder-creation endpoint where no Configurator account
    exists yet (bootstrapping flow).
    """
    token = _extract_shared_token(x_config_token, authorization)
    if not token or token != settings.CONFIGURATOR_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing configurator credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def verify_jwt_or_shared_password(
    x_config_token: Optional[str] = Header(default=None, alias="X-Config-Token"),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> dict:
    """Bootstrap-flow dependency accepting either a JWT or the shared password.

    The configurator console previously used the shared password for elder
    creation, but after JWT migration the frontend sends `Authorization:
    Bearer <jwt>` for logged-in users. This dependency tries JWT first, then
    falls back to the shared password (still required for first-time bootstrap
    where no Configurator account exists yet).
    """
    # 1) Try JWT path first.
    if authorization:
        value = authorization.strip()
        if value.lower().startswith("bearer "):
            token = value[7:].strip()
            try:
                payload = jwt.decode(
                    token, settings.SECRET_KEY, algorithms=["HS256"]
                )
                return {
                    "auth": "jwt",
                    "configurator_id": payload["sub"],
                    "elder_id": payload.get("elder_id"),
                }
            except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, KeyError):
                # Fall through to shared-password check.
                pass

    # 2) Fall back to shared-password check (X-Config-Token or raw Bearer).
    shared_token = _extract_shared_token(x_config_token, authorization)
    if shared_token and shared_token == settings.CONFIGURATOR_PASSWORD:
        return {"auth": "shared_password"}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing configurator credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _ensure_owns_elder(elder_id: str, current_user: dict) -> None:
    """Raise 403 unless the JWT-authenticated user owns the given elder."""
    if str(elder_id) != current_user.get("elder_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this elder",
        )


# -------------------------- Schemas --------------------------


class LoginRequest(BaseModel):
    login_name: str = Field(..., min_length=1, max_length=128)
    password: str = Field(..., min_length=1, max_length=128)


class LoginResponse(BaseModel):
    token: str
    message: str


class CreateElderRequest(BaseModel):
    nickname: str = Field(default="", max_length=64)
    profile_text: str = Field(default="", max_length=10000)
    contributor_relationship: str = Field(..., min_length=1, max_length=32)
    contributor_name: str = Field(default="", max_length=64)
    contributor_phone: Optional[str] = Field(default=None, max_length=20)
    login_name: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Login identifier for the configurator account; required for subsequent JWT-based login.",
    )


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
    contributor_relationship: str = Field(default="", max_length=32)


class UpdateProfileResponse(BaseModel):
    elder_id: str
    summary: str
    understanding_doc_version: int


class ElderListItem(BaseModel):
    elder_id: str
    nickname: Optional[str]
    status: str
    created_at: str
    profile_version: Optional[int] = None


class ElderListResponse(BaseModel):
    items: list[ElderListItem]
    total: int


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


@router.get(
    "/elders",
    response_model=ElderListResponse,
)
async def list_elders(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_configurator),
) -> ElderListResponse:
    """List elders owned by the authenticated configurator."""
    try:
        owned_elder_id = uuid.UUID(current_user["elder_id"])
    except (ValueError, TypeError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    stmt = (
        select(Elder)
        .where(Elder.id == owned_elder_id)
        .order_by(Elder.created_at.desc())
    )
    result = await db.execute(stmt)
    elders = result.scalars().all()

    items = []
    for elder in elders:
        profile = await _latest_profile(db, elder.id)
        items.append(ElderListItem(
            elder_id=str(elder.id),
            nickname=elder.nickname,
            status=elder.status,
            created_at=elder.created_at.isoformat() if elder.created_at else "",
            profile_version=profile.version if profile else None,
        ))

    return ElderListResponse(items=items, total=len(items))


@router.post("/auth/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Validate the shared password + look up Configurator by login_name.

    On success, issue a JWT (HS256, 7-day expiry) carrying the configurator's
    id and the elder_id they own. Subsequent requests must send it as
    `Authorization: Bearer <jwt>`.
    """
    if payload.password != settings.CONFIGURATOR_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
        )

    stmt = select(Configurator).where(Configurator.login_name == payload.login_name.strip())
    result = await db.execute(stmt)
    configurator = result.scalar_one_or_none()
    if configurator is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configurator not found for the given login_name",
        )

    token = _create_jwt(configurator.id, configurator.elder_id)
    return LoginResponse(token=token, message="Login successful")


@router.post(
    "/elders",
    response_model=CreateElderResponse,
)
async def create_elder(
    payload: CreateElderRequest,
    db: AsyncSession = Depends(get_db),
    credentials: dict = Depends(verify_jwt_or_shared_password),
) -> CreateElderResponse:
    """Create a new elder + initial understanding document.

    This is the bootstrap flow: it is gated by the shared configurator
    password (no Configurator account exists yet for the caller). The newly
    created Configurator's `login_name` is what the user will use on the
    JWT-based login endpoint afterwards.

    Steps:
    1. Insert Elder (with placeholder wechat_user_id since not from WeChat yet).
    2. Insert Configurator linked to the elder (using supplied login_name when
       provided; otherwise a generated one).
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

    supplied_login_name = (payload.login_name or "").strip()
    if supplied_login_name:
        existing_stmt = select(Configurator).where(Configurator.login_name == supplied_login_name)
        existing_result = await db.execute(existing_stmt)
        if existing_result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="login_name already in use",
            )
        login_name_value = supplied_login_name
    else:
        login_name_value = f"{placeholder_wechat_id}_{uuid.uuid4().hex[:8]}"

    configurator = Configurator(
        elder_id=elder.id,
        login_name=login_name_value,
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
)
async def get_elder(
    elder_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_configurator),
) -> ElderDetailResponse:
    """Return elder basic info plus the latest profile version + summary."""
    _ensure_owns_elder(elder_id, current_user)
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
)
async def append_profile(
    elder_id: str,
    payload: UpdateProfileRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_configurator),
) -> UpdateProfileResponse:
    """Append/merge new configurator-supplied text into the latest understanding doc.

    Stores the result as a new ElderProfile row with version = previous + 1.
    """
    _ensure_owns_elder(elder_id, current_user)
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
