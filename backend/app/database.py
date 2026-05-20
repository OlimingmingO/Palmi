"""SQLAlchemy engines and session factories (async + sync)."""
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_ENV == "development",
    pool_size=20,
    max_overflow=10,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Sync engine and session factory for Celery tasks
sync_engine = create_engine(
    settings.DATABASE_URL_SYNC,
    echo=settings.APP_ENV == "development",
    pool_pre_ping=True,
)

sync_session_factory = sessionmaker(bind=sync_engine, expire_on_commit=False)


async def get_db() -> AsyncSession:
    """FastAPI dependency: yield an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
