from __future__ import annotations

from typing import List, Optional

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Response,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from . import crud, schemas
from .database import get_async_session


app = FastAPI(title="Tech Forum Monitor API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_session() -> AsyncSession:
    async with get_async_session() as session:
        yield session


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get(
    "/api/v1/topics",
    response_model=schemas.PaginatedResponse[schemas.TopicRead],
)
async def list_topics(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> schemas.PaginatedResponse[schemas.TopicRead]:
    topics, total = await crud.list_topics(session, skip=skip, limit=limit)
    items = [schemas.TopicRead.model_validate(topic) for topic in topics]
    return schemas.PaginatedResponse[schemas.TopicRead](
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )


@app.post(
    "/api/v1/topics",
    response_model=schemas.TopicRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_topic(
    topic_in: schemas.TopicCreate, session: AsyncSession = Depends(get_session)
) -> schemas.TopicRead:
    try:
        topic = await crud.create_topic(session, topic_in)
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Topic with the same name already exists.",
        ) from exc
    return schemas.TopicRead.model_validate(topic)


@app.get(
    "/api/v1/topics/{topic_id}",
    response_model=schemas.TopicRead,
)
async def get_topic(
    topic_id: int, session: AsyncSession = Depends(get_session)
) -> schemas.TopicRead:
    topic = await crud.get_topic(session, topic_id)
    if not topic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found.")
    return schemas.TopicRead.model_validate(topic)


@app.put(
    "/api/v1/topics/{topic_id}",
    response_model=schemas.TopicRead,
)
async def update_topic(
    topic_id: int,
    topic_in: schemas.TopicUpdate,
    session: AsyncSession = Depends(get_session),
) -> schemas.TopicRead:
    topic = await crud.get_topic(session, topic_id)
    if not topic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found.")
    try:
        updated = await crud.update_topic(session, topic, topic_in)
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Topic with the same name already exists.",
        ) from exc
    return schemas.TopicRead.model_validate(updated)


@app.delete(
    "/api/v1/topics/{topic_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_topic(
    topic_id: int, session: AsyncSession = Depends(get_session)
) -> Response:
    topic = await crud.get_topic(session, topic_id)
    if not topic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found.")
    await crud.delete_topic(session, topic)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get(
    "/api/v1/posts",
    response_model=schemas.PaginatedResponse[schemas.PostRead],
)
async def list_posts(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    topic_id: Optional[int] = Query(None, ge=1),
    source: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
) -> schemas.PaginatedResponse[schemas.PostRead]:
    posts, total = await crud.list_posts(
        session,
        skip=skip,
        limit=limit,
        topic_id=topic_id,
        source=source,
    )
    items = [schemas.PostRead.model_validate(post) for post in posts]
    return schemas.PaginatedResponse[schemas.PostRead](
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )


@app.get(
    "/api/v1/logs",
    response_model=schemas.PaginatedResponse[schemas.PushLogRead],
)
async def list_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    session: AsyncSession = Depends(get_session),
) -> schemas.PaginatedResponse[schemas.PushLogRead]:
    logs, total = await crud.list_push_logs(
        session,
        skip=skip,
        limit=limit,
        status=status_filter,
    )
    items = [schemas.PushLogRead.model_validate(log) for log in logs]
    return schemas.PaginatedResponse[schemas.PushLogRead](
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )


@app.get("/api/v1/system/stats")
async def system_stats(
    session: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    return await crud.get_system_stats(session)
