from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app import crud, schemas
from app import models
from .conftest import AsyncSessionWrapper


@pytest.mark.asyncio
async def test_create_get_update_delete_topic(session: AsyncSessionWrapper) -> None:
    topic_in = schemas.TopicCreate(
        name="V2EX Python",
        source="v2ex",
        feed_url="https://www.v2ex.com/rss/node/python",
        keywords=["python", "fastapi"],
        is_active=True,
    )
    created = await crud.create_topic(session, topic_in)
    assert created.id is not None

    fetched = await crud.get_topic(session, created.id)
    assert fetched is not None
    assert fetched.name == "V2EX Python"

    updated = await crud.update_topic(
        session,
        fetched,
        schemas.TopicUpdate(is_active=False, keywords=["asyncio"]),
    )
    assert updated.is_active is False
    assert updated.keywords == ["asyncio"]

    topics, total = await crud.list_topics(session, skip=0, limit=10)
    assert total == 1
    assert len(topics) == 1

    await crud.delete_topic(session, updated)
    topics_after_delete, total_after_delete = await crud.list_topics(session, 0, 10)
    assert total_after_delete == 0
    assert topics_after_delete == []


@pytest.mark.asyncio
async def test_list_posts_filters(session: AsyncSessionWrapper) -> None:
    base_time = datetime.now(timezone.utc)
    topic_a = models.Topic(
        name="NodeSeek",
        source="nodeseek",
        feed_url="https://www.nodeseek.com/rss",
        keywords=["neo"],
        is_active=True,
    )
    topic_b = models.Topic(
        name="Linux.do",
        source="linux.do",
        feed_url="https://linux.do/rss",
        keywords=["linux"],
        is_active=True,
    )
    session.add_all([topic_a, topic_b])
    await session.flush()

    posts = [
        models.Post(
            topic_id=topic_a.id,
            title="NodeSeek Post 1",
            content="content",
            link="https://nodeseek.com/p/1",
            uid="nodeseek:1",
            published_at=base_time,
            created_at=base_time,
        ),
        models.Post(
            topic_id=topic_a.id,
            title="NodeSeek Post 2",
            content=None,
            link="https://nodeseek.com/p/2",
            uid="nodeseek:2",
            published_at=base_time + timedelta(minutes=1),
            created_at=base_time + timedelta(minutes=1),
        ),
        models.Post(
            topic_id=topic_b.id,
            title="Linux.do Post 1",
            content="linux",
            link="https://linux.do/p/1",
            uid="linux:1",
            published_at=base_time + timedelta(minutes=2),
            created_at=base_time + timedelta(minutes=2),
        ),
    ]
    session.add_all(posts)
    await session.commit()

    all_posts, total = await crud.list_posts(session, skip=0, limit=10)
    assert total == 3
    assert [post.uid for post in all_posts] == ["linux:1", "nodeseek:2", "nodeseek:1"]

    filtered_by_topic, total_topic = await crud.list_posts(
        session, skip=0, limit=10, topic_id=topic_a.id
    )
    assert total_topic == 2
    assert all(post.topic_id == topic_a.id for post in filtered_by_topic)

    filtered_by_source, total_source = await crud.list_posts(
        session, skip=0, limit=10, source="linux.do"
    )
    assert total_source == 1
    assert filtered_by_source[0].topic_id == topic_b.id


@pytest.mark.asyncio
async def test_list_push_logs(session: AsyncSessionWrapper) -> None:
    topic = models.Topic(
        name="V2EX Hot",
        source="v2ex",
        feed_url="https://www.v2ex.com/rss",
        keywords=["hot"],
        is_active=True,
    )
    session.add(topic)
    await session.flush()

    post = models.Post(
        topic_id=topic.id,
        title="Hot post",
        content="hot content",
        link="https://www.v2ex.com/t/1",
        uid="v2ex:1",
        published_at=datetime.now(timezone.utc),
    )
    session.add(post)
    await session.flush()

    logs = [
        models.PushLog(post_id=post.id, status="pending"),
        models.PushLog(post_id=post.id, status="success"),
    ]
    session.add_all(logs)
    await session.commit()

    all_logs, total_logs = await crud.list_push_logs(session, skip=0, limit=10)
    assert total_logs == 2
    assert {log.status for log in all_logs} == {"pending", "success"}

    success_logs, total_success = await crud.list_push_logs(
        session, skip=0, limit=10, status="success"
    )
    assert total_success == 1
    assert success_logs[0].status == "success"
