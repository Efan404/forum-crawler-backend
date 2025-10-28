from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from app.models import Post, PushLog, Topic
from tests.conftest import AsyncSessionWrapper


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_topics_crud_flow(
    client: AsyncClient,
) -> None:
    payload = {
        "name": "V2EX Python",
        "source": "v2ex",
        "feed_url": "https://www.v2ex.com/rss/node/python",
        "keywords": ["python"],
        "is_active": True,
    }

    created = await client.post("/api/v1/topics", json=payload)
    assert created.status_code == 201
    created_body = created.json()
    topic_id = created_body["id"]
    assert created_body["name"] == payload["name"]

    fetched = await client.get(f"/api/v1/topics/{topic_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == topic_id

    updated = await client.put(
        f"/api/v1/topics/{topic_id}",
        json={"is_active": False, "keywords": ["asyncio"]},
    )
    assert updated.status_code == 200
    update_body = updated.json()
    assert update_body["is_active"] is False
    assert update_body["keywords"] == ["asyncio"]

    listed = await client.get("/api/v1/topics?skip=0&limit=10")
    assert listed.status_code == 200
    list_body = listed.json()
    assert list_body["total"] == 1
    assert len(list_body["items"]) == 1

    deleted = await client.delete(f"/api/v1/topics/{topic_id}")
    assert deleted.status_code == 204

    missing = await client.get(f"/api/v1/topics/{topic_id}")
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_topics_duplicate_name_returns_error(
    client: AsyncClient,
) -> None:
    payload = {
        "name": "Duplicate",
        "source": "v2ex",
        "feed_url": "https://www.v2ex.com/rss",
        "keywords": [],
        "is_active": True,
    }
    first = await client.post("/api/v1/topics", json=payload)
    assert first.status_code == 201

    duplicate = await client.post("/api/v1/topics", json=payload)
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"] == "Topic with the same name already exists."


@pytest.mark.asyncio
async def test_posts_listing_and_filters(
    client: AsyncClient, session: AsyncSessionWrapper
) -> None:
    base_time = datetime.now(timezone.utc)
    topic_v2ex = Topic(
        name="V2EX Hot",
        source="v2ex",
        feed_url="https://www.v2ex.com/rss",
        keywords=["hot"],
        is_active=True,
    )
    topic_linux = Topic(
        name="Linux Do",
        source="linux.do",
        feed_url="https://linux.do/rss",
        keywords=["linux"],
        is_active=True,
    )
    session.add_all([topic_v2ex, topic_linux])
    await session.flush()

    session.add_all(
        [
            Post(
                topic_id=topic_v2ex.id,
                title="V2EX Post 1",
                content="discussion",
                link="https://www.v2ex.com/t/1",
                uid="v2ex:1",
                published_at=base_time,
                created_at=base_time,
            ),
            Post(
                topic_id=topic_v2ex.id,
                title="V2EX Post 2",
                content=None,
                link="https://www.v2ex.com/t/2",
                uid="v2ex:2",
                published_at=base_time + timedelta(minutes=1),
                created_at=base_time + timedelta(minutes=1),
            ),
            Post(
                topic_id=topic_linux.id,
                title="Linux Post 1",
                content="linux",
                link="https://linux.do/t/1",
                uid="linux:1",
                published_at=base_time + timedelta(minutes=2),
                created_at=base_time + timedelta(minutes=2),
            ),
        ]
    )
    await session.commit()

    response = await client.get("/api/v1/posts?skip=0&limit=2")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["items"][0]["uid"] == "linux:1"

    filtered_topic = await client.get(f"/api/v1/posts?topic_id={topic_v2ex.id}")
    assert filtered_topic.status_code == 200
    filtered_topic_body = filtered_topic.json()
    assert filtered_topic_body["total"] == 2
    assert all(item["topic_id"] == topic_v2ex.id for item in filtered_topic_body["items"])

    filtered_source = await client.get("/api/v1/posts?source=linux.do")
    assert filtered_source.status_code == 200
    filtered_source_body = filtered_source.json()
    assert filtered_source_body["total"] == 1
    assert filtered_source_body["items"][0]["topic_id"] == topic_linux.id


@pytest.mark.asyncio
async def test_logs_listing_and_system_stats(
    client: AsyncClient, session: AsyncSessionWrapper
) -> None:
    topic = Topic(
        name="Stats Topic",
        source="v2ex",
        feed_url="https://www.v2ex.com/rss",
        keywords=["stat"],
        is_active=True,
    )
    session.add(topic)
    await session.flush()

    post = Post(
        topic_id=topic.id,
        title="Stats Post",
        content="content",
        link="https://www.v2ex.com/t/100",
        uid="v2ex:100",
        published_at=datetime.now(timezone.utc),
    )
    session.add(post)
    await session.flush()

    session.add_all(
        [
            PushLog(post_id=post.id, status="success"),
            PushLog(post_id=post.id, status="failed"),
        ]
    )
    await session.commit()

    logs = await client.get("/api/v1/logs")
    assert logs.status_code == 200
    logs_body = logs.json()
    assert logs_body["total"] == 2

    filtered_logs = await client.get("/api/v1/logs?status=success")
    assert filtered_logs.status_code == 200
    filtered_logs_body = filtered_logs.json()
    assert filtered_logs_body["total"] == 1
    assert filtered_logs_body["items"][0]["status"] == "success"

    stats = await client.get("/api/v1/system/stats")
    assert stats.status_code == 200
    stats_body = stats.json()
    assert stats_body == {
        "topics_total": 1,
        "active_topics": 1,
        "posts_total": 1,
        "logs_total": 2,
    }
