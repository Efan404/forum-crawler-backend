from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any, Dict

from celery import Celery
from celery.schedules import crontab
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from .config import settings
from .database import sync_engine
from .fetchers import fetch_feed, match_keywords
from . import models

celery_app = Celery(
    "app.tasks",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_app.conf.timezone = "UTC"

celery_app.conf.beat_schedule = {
    "fetch-every-5-minutes": {
        "task": "app.tasks.fetch_all_topics",
        "schedule": crontab(minute="*/5"),
    }
}

SessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False, future=True)


def _get_active_topics(session: Session) -> Sequence[models.Topic]:
    return (
        session.execute(select(models.Topic).where(models.Topic.is_active))
        .scalars()
        .all()
    )


def _uid_exists(session: Session, uid: str) -> bool:
    return (
        session.execute(select(models.Post.id).where(models.Post.uid == uid))
        .scalar_one_or_none()
        is not None
    )


def _should_keep_entry(entry: Dict[str, Any], keywords: Sequence[str] | None) -> bool:
    text_parts = [entry.get("title"), entry.get("summary")]
    combined = " ".join(part for part in text_parts if part)
    keyword_list = list(keywords) if keywords else []
    return match_keywords(combined, keyword_list)


@celery_app.task(name="app.tasks.fetch_all_topics")
def fetch_all_topics() -> Dict[str, int]:
    session = SessionLocal()
    stats = {"topics_checked": 0, "posts_created": 0, "duplicates": 0}
    try:
        topics = _get_active_topics(session)
        stats["topics_checked"] = len(topics)

        for topic in topics:
            entries = asyncio.run(fetch_feed(topic.source, topic.feed_url))
            for entry in entries:
                uid = entry["uid"]

                if _uid_exists(session, uid):
                    stats["duplicates"] += 1
                    continue

                if not _should_keep_entry(entry, topic.keywords):
                    continue

                post = models.Post(
                    topic_id=topic.id,
                    title=entry["title"],
                    content=entry.get("summary"),
                    link=entry["link"],
                    uid=uid,
                    published_at=entry["published_at"],
                )
                session.add(post)
                session.flush()

                log = models.PushLog(post_id=post.id, status="pending")
                session.add(log)
                stats["posts_created"] += 1

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    return stats
