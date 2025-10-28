from contextlib import asynccontextmanager

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import settings


async_engine = create_async_engine(settings.database_url, echo=False, future=True)
async_session_factory = async_sessionmaker(
    async_engine,
    expire_on_commit=False,
)

sync_engine = create_engine(settings.sync_database_url, pool_pre_ping=True, future=True)


@asynccontextmanager
async def get_async_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session

