from __future__ import annotations

from typing import Optional, Sequence, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from . import models, schemas


async def create_topic(
    session: AsyncSession, topic_in: schemas.TopicCreate
) -> models.Topic:
    topic = models.Topic(**topic_in.model_dump())
    session.add(topic)
    await session.commit()
    await session.refresh(topic)
    return topic


async def get_topic(session: AsyncSession, topic_id: int) -> Optional[models.Topic]:
    return await session.get(models.Topic, topic_id)


async def get_topic_by_name(
    session: AsyncSession, name: str
) -> Optional[models.Topic]:
    result = await session.execute(
        select(models.Topic).where(models.Topic.name == name)
    )
    return result.scalar_one_or_none()


async def list_topics(
    session: AsyncSession, skip: int = 0, limit: int = 20
) -> Tuple[Sequence[models.Topic], int]:
    total_result = await session.execute(
        select(func.count()).select_from(models.Topic)
    )
    total = total_result.scalar_one()

    result = await session.execute(
        select(models.Topic)
        .order_by(models.Topic.id)
        .offset(skip)
        .limit(limit)
    )
    topics = result.scalars().all()
    return topics, total


async def update_topic(
    session: AsyncSession, topic: models.Topic, topic_in: schemas.TopicUpdate
) -> models.Topic:
    for field, value in topic_in.model_dump(exclude_unset=True).items():
        setattr(topic, field, value)
    await session.commit()
    await session.refresh(topic)
    return topic


async def delete_topic(session: AsyncSession, topic: models.Topic) -> None:
    await session.delete(topic)
    await session.commit()


async def list_posts(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    topic_id: Optional[int] = None,
    source: Optional[str] = None,
) -> Tuple[Sequence[models.Post], int]:
    stmt = select(models.Post).order_by(models.Post.created_at.desc())
    count_stmt = select(func.count()).select_from(models.Post)

    if topic_id is not None:
        stmt = stmt.where(models.Post.topic_id == topic_id)
        count_stmt = count_stmt.where(models.Post.topic_id == topic_id)

    if source is not None:
        stmt = stmt.join(models.Topic).where(models.Topic.source == source)
        count_stmt = count_stmt.join(models.Topic).where(models.Topic.source == source)

    count_result = await session.execute(count_stmt)
    total = count_result.scalar_one()

    result = await session.execute(
        stmt.options(selectinload(models.Post.topic)).offset(skip).limit(limit)
    )
    posts = result.scalars().all()
    return posts, total


async def list_push_logs(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
) -> Tuple[Sequence[models.PushLog], int]:
    stmt = select(models.PushLog).order_by(models.PushLog.created_at.desc())
    count_stmt = select(func.count()).select_from(models.PushLog)

    if status is not None:
        stmt = stmt.where(models.PushLog.status == status)
        count_stmt = count_stmt.where(models.PushLog.status == status)

    count_result = await session.execute(count_stmt)
    total = count_result.scalar_one()

    result = await session.execute(
        stmt.options(selectinload(models.PushLog.post))
        .offset(skip)
        .limit(limit)
    )
    logs = result.scalars().all()
    return logs, total


async def get_system_stats(session: AsyncSession) -> dict:
    topics_total = await session.scalar(
        select(func.count()).select_from(models.Topic)
    )
    active_topics = await session.scalar(
        select(func.count()).select_from(models.Topic).where(models.Topic.is_active)
    )
    posts_total = await session.scalar(
        select(func.count()).select_from(models.Post)
    )
    logs_total = await session.scalar(
        select(func.count()).select_from(models.PushLog)
    )
    return {
        "topics_total": topics_total or 0,
        "active_topics": active_topics or 0,
        "posts_total": posts_total or 0,
        "logs_total": logs_total or 0,
    }
