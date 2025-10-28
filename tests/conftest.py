from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/test_db"
)
os.environ.setdefault(
    "SYNC_DATABASE_URL", "sqlite:///./test.db"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from app.main import app, get_session
from app.models import Base


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    future=True,
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class AsyncSessionWrapper:
    def __init__(self):
        self._session = SessionLocal()

    def add(self, instance) -> None:
        self._session.add(instance)

    def add_all(self, instances) -> None:
        self._session.add_all(instances)

    async def execute(self, statement):
        return await asyncio.to_thread(self._session.execute, statement)

    async def scalar(self, statement):
        return await asyncio.to_thread(self._session.scalar, statement)

    async def get(self, model, ident):
        return await asyncio.to_thread(self._session.get, model, ident)

    async def commit(self) -> None:
        await asyncio.to_thread(self._session.commit)

    async def rollback(self) -> None:
        await asyncio.to_thread(self._session.rollback)

    async def refresh(self, instance) -> None:
        await asyncio.to_thread(self._session.refresh, instance)

    async def delete(self, instance) -> None:
        await asyncio.to_thread(self._session.delete, instance)

    async def flush(self) -> None:
        await asyncio.to_thread(self._session.flush)

    async def close(self) -> None:
        await asyncio.to_thread(self._session.close)


@pytest.fixture(scope="session")
def event_loop() -> AsyncIterator[asyncio.AbstractEventLoop]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def prepare_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def session_context() -> AsyncIterator[AsyncSessionWrapper]:
    session = AsyncSessionWrapper()
    try:
        yield session
    finally:
        await session.rollback()
        await session.close()


@pytest_asyncio.fixture(scope="function")
async def session() -> AsyncIterator[AsyncSessionWrapper]:
    async with session_context() as test_session:
        yield test_session


@pytest_asyncio.fixture(scope="function")
async def client() -> AsyncIterator[AsyncClient]:
    async def override_get_session() -> AsyncIterator[AsyncSessionWrapper]:
        async with session_context() as db_session:
            yield db_session

    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(app=app, base_url="http://testserver") as test_client:
        yield test_client
    app.dependency_overrides.clear()
