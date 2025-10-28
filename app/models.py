from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Topic(TimestampMixin, Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    feed_url: Mapped[str] = mapped_column(String(500), nullable=False)
    keywords: Mapped[List[str]] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    posts: Mapped[List["Post"]] = relationship(
        back_populates="topic", cascade="all, delete-orphan"
    )


class Post(CreatedAtMixin, Base):
    __tablename__ = "posts"
    __table_args__ = (UniqueConstraint("uid", name="uq_posts_uid"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, default=None)
    link: Mapped[str] = mapped_column(String(500), nullable=False)
    uid: Mapped[str] = mapped_column(String(255), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_pushed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    topic: Mapped["Topic"] = relationship(back_populates="posts")
    push_logs: Mapped[List["PushLog"]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )


class PushLog(CreatedAtMixin, Base):
    __tablename__ = "push_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    message: Mapped[Optional[str]] = mapped_column(Text, default=None)

    post: Mapped["Post"] = relationship(back_populates="push_logs")

