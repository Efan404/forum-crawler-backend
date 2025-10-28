from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models, tasks


@pytest.fixture
def task_session_factory(monkeypatch: pytest.MonkeyPatch):
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


def _sample_entries():
    now = datetime.now(timezone.utc)
    return [
        {
            "title": "Python release",
            "link": "https://example.com/python",
            "summary": "Python and FastAPI updates",
            "uid": "v2ex:https://example.com/python",
            "published_at": now,
        },
        {
            "title": "Unrelated",
            "link": "https://example.com/other",
            "summary": "Random news",
            "uid": "v2ex:https://example.com/other",
            "published_at": now,
        },
    ]


def test_fetch_all_topics_creates_posts_and_logs(
    task_session_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    entries = _sample_entries()

    async def fake_fetch_feed(source: str, feed_url: str):
        assert source == "v2ex"
        return entries

    monkeypatch.setattr(tasks, "fetch_feed", fake_fetch_feed)

    session = task_session_factory()
    topic = models.Topic(
        name="V2EX Python",
        source="v2ex",
        feed_url="https://www.v2ex.com/rss",
        keywords=["python"],
        is_active=True,
    )
    session.add(topic)
    session.commit()
    session.close()

    stats = tasks.fetch_all_topics()
    assert stats == {"topics_checked": 1, "posts_created": 1, "duplicates": 0}

    session = task_session_factory()
    posts = session.execute(select(models.Post)).scalars().all()
    assert len(posts) == 1
    assert posts[0].uid == "v2ex:https://example.com/python"

    logs = session.execute(select(models.PushLog)).scalars().all()
    assert len(logs) == 1
    assert logs[0].status == "pending"
    session.close()

    stats_second = tasks.fetch_all_topics()
    assert stats_second["duplicates"] == 1
    assert stats_second["posts_created"] == 0
