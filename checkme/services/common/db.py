"""
AFASA 2.0 - Database Session Management with RLS
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from sqlalchemy.orm import DeclarativeBase

from .settings import get_settings

settings = get_settings()

# Convert sync URL to async
db_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(db_url, echo=False, pool_pre_ping=True)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


class Base(DeclarativeBase):
    pass


@asynccontextmanager
async def get_tenant_session(tenant_id: str) -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session with RLS tenant context set.
    This MUST be used for all tenant-scoped queries.
    """
    async with AsyncSessionLocal() as session:
        # Set the tenant context for RLS
        await session.execute(text(f"SET app.tenant_id = '{tenant_id}'"))
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            # Clear the tenant context
            await session.execute(text("RESET app.tenant_id"))


async def get_admin_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session WITHOUT RLS context.
    Use only for admin/system operations.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
