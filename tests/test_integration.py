"""Integration tests for the complete workflow."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from app.models import Post, PushLog, Topic
from .conftest import AsyncSessionWrapper


@pytest.mark.asyncio
async def test_complete_workflow(
    client: AsyncClient, session: AsyncSessionWrapper
) -> None:
    """Test complete workflow: create topic -> add post -> check logs."""
    # Step 1: Create a topic
    topic_response = await client.post(
        "/api/v1/topics",
        json={
            "name": "Integration Test Topic",
            "source": "v2ex",
            "feed_url": "https://www.v2ex.com/rss",
            "keywords": ["python"],
            "is_active": True,
        },
    )
    assert topic_response.status_code == 201
    topic_data = topic_response.json()
    topic_id = topic_data["id"]

    # Step 2: Verify the topic was created
    get_topic_response = await client.get(f"/api/v1/topics/{topic_id}")
    assert get_topic_response.status_code == 200

    # Step 3: Manually add a post (simulating what the task would do)
    post = Post(
        topic_id=topic_id,
        title="Integration Test Post",
        content="This is a test post with python keyword",
        link="https://example.com/post1",
        uid="v2ex:integration:1",
        published_at=datetime.now(timezone.utc),
    )
    session.add(post)
    await session.flush()

    # Step 4: Add a push log for the post
    log = PushLog(post_id=post.id, status="pending")
    session.add(log)
    await session.commit()

    # Step 5: Verify posts can be listed
    posts_response = await client.get(f"/api/v1/posts?topic_id={topic_id}")
    assert posts_response.status_code == 200
    posts_data = posts_response.json()
    assert posts_data["total"] == 1
    assert posts_data["items"][0]["title"] == "Integration Test Post"

    # Step 6: Verify logs can be listed
    logs_response = await client.get("/api/v1/logs")
    assert logs_response.status_code == 200
    logs_data = logs_response.json()
    assert logs_data["total"] == 1
    assert logs_data["items"][0]["status"] == "pending"

    # Step 7: Verify system stats are updated
    stats_response = await client.get("/api/v1/system/stats")
    assert stats_response.status_code == 200
    stats_data = stats_response.json()
    assert stats_data["topics_total"] == 1
    assert stats_data["active_topics"] == 1
    assert stats_data["posts_total"] == 1
    assert stats_data["logs_total"] == 1

    # Step 8: Deactivate the topic
    update_response = await client.put(
        f"/api/v1/topics/{topic_id}",
        json={"is_active": False},
    )
    assert update_response.status_code == 200

    # Step 9: Verify active topics count decreased
    stats_response = await client.get("/api/v1/system/stats")
    stats_data = stats_response.json()
    assert stats_data["active_topics"] == 0
    assert stats_data["topics_total"] == 1

    # Step 10: Delete the topic
    delete_response = await client.delete(f"/api/v1/topics/{topic_id}")
    assert delete_response.status_code == 204


@pytest.mark.asyncio
async def test_multiple_topics_with_different_sources(
    client: AsyncClient, session: AsyncSessionWrapper
) -> None:
    """Test creating multiple topics from different sources."""
    sources = ["v2ex", "nodeseek", "linux.do"]
    topic_ids = []

    # Create topics for each source
    for source in sources:
        response = await client.post(
            "/api/v1/topics",
            json={
                "name": f"{source.title()} Topic",
                "source": source,
                "feed_url": f"https://{source}.com/rss",
                "keywords": ["test"],
                "is_active": True,
            },
        )
        assert response.status_code == 201
        topic_ids.append(response.json()["id"])

    # Add posts for each topic
    for idx, topic_id in enumerate(topic_ids):
        post = Post(
            topic_id=topic_id,
            title=f"Post from {sources[idx]}",
            content="Test content",
            link=f"https://{sources[idx]}.com/post",
            uid=f"{sources[idx]}:test:1",
            published_at=datetime.now(timezone.utc),
        )
        session.add(post)
    await session.commit()

    # Filter posts by each source
    for source in sources:
        response = await client.get(f"/api/v1/posts?source={source}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert source in data["items"][0]["title"].lower()


@pytest.mark.asyncio
async def test_keyword_filtering_in_posts(session: AsyncSessionWrapper) -> None:
    """Test that keyword filtering works correctly."""
    from app.fetchers import match_keywords

    # Test exact match
    assert match_keywords("Python programming guide", ["python"]) is True

    # Test case insensitive
    assert match_keywords("PYTHON Programming", ["python"]) is True

    # Test multiple keywords (any match)
    assert match_keywords("FastAPI tutorial", ["python", "fastapi"]) is True

    # Test no match
    assert match_keywords("JavaScript tutorial", ["python"]) is False

    # Test empty keywords (should match everything)
    assert match_keywords("Any content", []) is True

    # Test None text with keywords
    assert match_keywords(None, ["python"]) is False

    # Test empty text
    assert match_keywords("", ["python"]) is False

    # Test keyword in title or summary
    combined_text = "FastAPI Framework Python async web framework"
    assert match_keywords(combined_text, ["fastapi", "django"]) is True


@pytest.mark.asyncio
async def test_post_deduplication(session: AsyncSessionWrapper) -> None:
    """Test that posts with duplicate UIDs are not created."""
    topic = Topic(
        name="Dedup Test Topic",
        source="v2ex",
        feed_url="https://example.com/rss",
        keywords=["test"],
        is_active=True,
    )
    session.add(topic)
    await session.flush()

    # Add first post
    post1 = Post(
        topic_id=topic.id,
        title="First Post",
        content="Content",
        link="https://example.com/post1",
        uid="v2ex:unique:1",
        published_at=datetime.now(timezone.utc),
    )
    session.add(post1)
    await session.commit()

    # Try to add duplicate post (same UID)
    from sqlalchemy.exc import IntegrityError

    post2 = Post(
        topic_id=topic.id,
        title="Duplicate Post",
        content="Different content",
        link="https://example.com/post2",
        uid="v2ex:unique:1",  # Same UID
        published_at=datetime.now(timezone.utc),
    )
    session.add(post2)

    # Should raise IntegrityError due to unique constraint
    with pytest.raises(IntegrityError):
        await session.commit()
