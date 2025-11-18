"""Additional API edge cases and error handling tests."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_update_nonexistent_topic_returns_404(client: AsyncClient) -> None:
    """Test updating a topic that doesn't exist."""
    response = await client.put(
        "/api/v1/topics/99999",
        json={"is_active": False},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_delete_nonexistent_topic_returns_404(client: AsyncClient) -> None:
    """Test deleting a topic that doesn't exist."""
    response = await client.delete("/api/v1/topics/99999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_nonexistent_topic_returns_404(client: AsyncClient) -> None:
    """Test getting a topic that doesn't exist."""
    response = await client.get("/api/v1/topics/99999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_update_topic_duplicate_name_returns_400(client: AsyncClient) -> None:
    """Test updating a topic with a name that already exists."""
    # Create two topics
    topic1 = await client.post(
        "/api/v1/topics",
        json={
            "name": "Topic 1",
            "source": "v2ex",
            "feed_url": "https://example.com/rss1",
            "keywords": [],
            "is_active": True,
        },
    )
    assert topic1.status_code == 201

    topic2 = await client.post(
        "/api/v1/topics",
        json={
            "name": "Topic 2",
            "source": "v2ex",
            "feed_url": "https://example.com/rss2",
            "keywords": [],
            "is_active": True,
        },
    )
    assert topic2.status_code == 201
    topic2_id = topic2.json()["id"]

    # Try to update topic2 with topic1's name
    response = await client.put(
        f"/api/v1/topics/{topic2_id}",
        json={"name": "Topic 1"},
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_topic_with_empty_keywords(client: AsyncClient) -> None:
    """Test creating a topic with empty keywords list."""
    response = await client.post(
        "/api/v1/topics",
        json={
            "name": "No Keywords Topic",
            "source": "v2ex",
            "feed_url": "https://example.com/rss",
            "keywords": [],
            "is_active": True,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["keywords"] == []


@pytest.mark.asyncio
async def test_list_topics_with_pagination_boundaries(client: AsyncClient) -> None:
    """Test topic listing with various pagination parameters."""
    # Create 5 topics
    for i in range(5):
        await client.post(
            "/api/v1/topics",
            json={
                "name": f"Topic {i}",
                "source": "v2ex",
                "feed_url": f"https://example.com/rss{i}",
                "keywords": [],
                "is_active": True,
            },
        )

    # Test with skip > total
    response = await client.get("/api/v1/topics?skip=100&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["items"]) == 0

    # Test with limit = 1
    response = await client.get("/api/v1/topics?skip=0&limit=1")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["items"]) == 1

    # Test with skip = 3, limit = 2
    response = await client.get("/api/v1/topics?skip=3&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_list_posts_with_invalid_filters(client: AsyncClient) -> None:
    """Test posts listing with non-existent topic_id."""
    response = await client.get("/api/v1/posts?topic_id=99999")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["items"]) == 0


@pytest.mark.asyncio
async def test_list_posts_with_nonexistent_source(client: AsyncClient) -> None:
    """Test posts listing with non-existent source."""
    response = await client.get("/api/v1/posts?source=nonexistent")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["items"]) == 0


@pytest.mark.asyncio
async def test_list_logs_with_invalid_status(client: AsyncClient) -> None:
    """Test logs listing with non-existent status."""
    response = await client.get("/api/v1/logs?status=invalid")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["items"]) == 0


@pytest.mark.asyncio
async def test_system_stats_with_empty_database(client: AsyncClient) -> None:
    """Test system stats when database is empty."""
    response = await client.get("/api/v1/system/stats")
    assert response.status_code == 200
    data = response.json()
    assert data == {
        "topics_total": 0,
        "active_topics": 0,
        "posts_total": 0,
        "logs_total": 0,
    }


@pytest.mark.asyncio
async def test_create_topic_with_very_long_keyword_list(client: AsyncClient) -> None:
    """Test creating a topic with many keywords."""
    keywords = [f"keyword{i}" for i in range(50)]
    response = await client.post(
        "/api/v1/topics",
        json={
            "name": "Many Keywords Topic",
            "source": "v2ex",
            "feed_url": "https://example.com/rss",
            "keywords": keywords,
            "is_active": True,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["keywords"]) == 50
