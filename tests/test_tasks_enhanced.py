"""Enhanced tasks tests including edge cases and error handling."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models, tasks


@pytest.fixture
def task_session_factory(monkeypatch: pytest.MonkeyPatch):
    """Create a test database session factory for tasks."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    models.Base.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    monkeypatch.setattr(tasks, "SessionLocal", SessionLocal)

    yield SessionLocal

    models.Base.metadata.drop_all(bind=engine)


def test_fetch_all_topics_with_no_active_topics(
    task_session_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test fetch_all_topics when no active topics exist."""
    session = task_session_factory()

    # Create an inactive topic
    topic = models.Topic(
        name="Inactive Topic",
        source="v2ex",
        feed_url="https://example.com/rss",
        keywords=["test"],
        is_active=False,  # Inactive
    )
    session.add(topic)
    session.commit()
    session.close()

    stats = tasks.fetch_all_topics()
    assert stats["topics_checked"] == 0
    assert stats["posts_created"] == 0
    assert stats["duplicates"] == 0


def test_fetch_all_topics_with_no_matching_keywords(
    task_session_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test fetch_all_topics when entries don't match keywords."""
    entries = [
        {
            "title": "JavaScript Tutorial",
            "link": "https://example.com/js",
            "summary": "Learn JavaScript",
            "uid": "v2ex:js:1",
            "published_at": datetime.now(timezone.utc),
        },
    ]

    async def fake_fetch_feed(source: str, feed_url: str):
        return entries

    monkeypatch.setattr(tasks, "fetch_feed", fake_fetch_feed)

    session = task_session_factory()
    topic = models.Topic(
        name="Python Only Topic",
        source="v2ex",
        feed_url="https://example.com/rss",
        keywords=["python"],  # Only matches python
        is_active=True,
    )
    session.add(topic)
    session.commit()
    session.close()

    stats = tasks.fetch_all_topics()
    assert stats["topics_checked"] == 1
    assert stats["posts_created"] == 0  # No matches
    assert stats["duplicates"] == 0


def test_fetch_all_topics_with_empty_keywords(
    task_session_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test fetch_all_topics with empty keywords (should accept all)."""
    entries = [
        {
            "title": "Any Topic",
            "link": "https://example.com/any",
            "summary": "Any content",
            "uid": "v2ex:any:1",
            "published_at": datetime.now(timezone.utc),
        },
    ]

    async def fake_fetch_feed(source: str, feed_url: str):
        return entries

    monkeypatch.setattr(tasks, "fetch_feed", fake_fetch_feed)

    session = task_session_factory()
    topic = models.Topic(
        name="Accept All Topic",
        source="v2ex",
        feed_url="https://example.com/rss",
        keywords=[],  # Empty keywords
        is_active=True,
    )
    session.add(topic)
    session.commit()
    session.close()

    stats = tasks.fetch_all_topics()
    assert stats["topics_checked"] == 1
    assert stats["posts_created"] == 1  # Should accept all


def test_fetch_all_topics_with_multiple_entries(
    task_session_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test fetch_all_topics with multiple entries, some matching."""
    now = datetime.now(timezone.utc)
    entries = [
        {
            "title": "Python Tutorial",
            "link": "https://example.com/python",
            "summary": "Learn Python",
            "uid": "v2ex:python:1",
            "published_at": now,
        },
        {
            "title": "JavaScript Guide",
            "link": "https://example.com/js",
            "summary": "Learn JS",
            "uid": "v2ex:js:1",
            "published_at": now,
        },
        {
            "title": "FastAPI Framework",
            "link": "https://example.com/fastapi",
            "summary": "Python FastAPI",
            "uid": "v2ex:fastapi:1",
            "published_at": now,
        },
    ]

    async def fake_fetch_feed(source: str, feed_url: str):
        return entries

    monkeypatch.setattr(tasks, "fetch_feed", fake_fetch_feed)

    session = task_session_factory()
    topic = models.Topic(
        name="Python Topic",
        source="v2ex",
        feed_url="https://example.com/rss",
        keywords=["python"],
        is_active=True,
    )
    session.add(topic)
    session.commit()
    session.close()

    stats = tasks.fetch_all_topics()
    assert stats["topics_checked"] == 1
    assert stats["posts_created"] == 2  # Python Tutorial and FastAPI Framework
    assert stats["duplicates"] == 0


def test_fetch_all_topics_creates_push_logs(
    task_session_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that fetch_all_topics creates push logs for new posts."""
    entries = [
        {
            "title": "Test Post",
            "link": "https://example.com/post",
            "summary": "Test content",
            "uid": "v2ex:test:1",
            "published_at": datetime.now(timezone.utc),
        },
    ]

    async def fake_fetch_feed(source: str, feed_url: str):
        return entries

    monkeypatch.setattr(tasks, "fetch_feed", fake_fetch_feed)

    session = task_session_factory()
    topic = models.Topic(
        name="Test Topic",
        source="v2ex",
        feed_url="https://example.com/rss",
        keywords=[],
        is_active=True,
    )
    session.add(topic)
    session.commit()
    session.close()

    tasks.fetch_all_topics()

    # Verify push log was created
    session = task_session_factory()
    logs = session.execute(select(models.PushLog)).scalars().all()
    assert len(logs) == 1
    assert logs[0].status == "pending"
    session.close()


def test_fetch_all_topics_with_multiple_active_topics(
    task_session_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test fetch_all_topics with multiple active topics."""
    v2ex_entries = [
        {
            "title": "V2EX Post",
            "link": "https://v2ex.com/post",
            "summary": "V2EX content",
            "uid": "v2ex:post:1",
            "published_at": datetime.now(timezone.utc),
        },
    ]

    nodeseek_entries = [
        {
            "title": "NodeSeek Post",
            "link": "https://nodeseek.com/post",
            "summary": "NodeSeek content",
            "uid": "nodeseek:post:1",
            "published_at": datetime.now(timezone.utc),
        },
    ]

    call_count = {"v2ex": 0, "nodeseek": 0}

    async def fake_fetch_feed(source: str, feed_url: str):
        call_count[source] += 1
        if source == "v2ex":
            return v2ex_entries
        return nodeseek_entries

    monkeypatch.setattr(tasks, "fetch_feed", fake_fetch_feed)

    session = task_session_factory()
    topic1 = models.Topic(
        name="V2EX Topic",
        source="v2ex",
        feed_url="https://v2ex.com/rss",
        keywords=[],
        is_active=True,
    )
    topic2 = models.Topic(
        name="NodeSeek Topic",
        source="nodeseek",
        feed_url="https://nodeseek.com/rss",
        keywords=[],
        is_active=True,
    )
    session.add_all([topic1, topic2])
    session.commit()
    session.close()

    stats = tasks.fetch_all_topics()
    assert stats["topics_checked"] == 2
    assert stats["posts_created"] == 2
    assert call_count["v2ex"] == 1
    assert call_count["nodeseek"] == 1


def test_should_keep_entry_with_various_inputs() -> None:
    """Test _should_keep_entry helper function."""
    # Match in title
    entry = {"title": "Python Tutorial", "summary": "Learn programming"}
    assert tasks._should_keep_entry(entry, ["python"]) is True

    # Match in summary
    entry = {"title": "Tutorial", "summary": "Learn Python programming"}
    assert tasks._should_keep_entry(entry, ["python"]) is True

    # Match in combined text
    entry = {"title": "Web Framework", "summary": "FastAPI is great"}
    assert tasks._should_keep_entry(entry, ["fastapi"]) is True

    # No match
    entry = {"title": "JavaScript", "summary": "Node.js tutorial"}
    assert tasks._should_keep_entry(entry, ["python"]) is False

    # Empty keywords (match all)
    entry = {"title": "Any Topic", "summary": "Any content"}
    assert tasks._should_keep_entry(entry, []) is True

    # None keywords (match all)
    entry = {"title": "Any Topic", "summary": "Any content"}
    assert tasks._should_keep_entry(entry, None) is True

    # Missing fields
    entry = {"title": None, "summary": None}
    assert tasks._should_keep_entry(entry, ["python"]) is False


def test_uid_exists_check(task_session_factory) -> None:
    """Test _uid_exists helper function."""
    session = task_session_factory()

    # Create a topic and post
    topic = models.Topic(
        name="Test Topic",
        source="v2ex",
        feed_url="https://example.com/rss",
        keywords=[],
        is_active=True,
    )
    session.add(topic)
    session.flush()

    post = models.Post(
        topic_id=topic.id,
        title="Test Post",
        content="Content",
        link="https://example.com/post",
        uid="v2ex:exists:1",
        published_at=datetime.now(timezone.utc),
    )
    session.add(post)
    session.commit()

    # Test existing UID
    assert tasks._uid_exists(session, "v2ex:exists:1") is True

    # Test non-existing UID
    assert tasks._uid_exists(session, "v2ex:notexists:1") is False

    session.close()
