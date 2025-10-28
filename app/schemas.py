from __future__ import annotations

from datetime import datetime
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field
from pydantic.generics import GenericModel


class TopicBase(BaseModel):
    name: str
    source: str
    feed_url: str
    keywords: List[str] = Field(default_factory=list)
    is_active: bool = True


class TopicCreate(TopicBase):
    pass


class TopicUpdate(BaseModel):
    name: Optional[str] = None
    source: Optional[str] = None
    feed_url: Optional[str] = None
    keywords: Optional[List[str]] = None
    is_active: Optional[bool] = None


class TopicRead(TopicBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PostBase(BaseModel):
    title: str
    content: Optional[str] = None
    link: str
    uid: str
    published_at: datetime
    is_pushed: bool = False


class PostCreate(PostBase):
    topic_id: int


class PostRead(PostBase):
    id: int
    topic_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class PushLogBase(BaseModel):
    status: str = "pending"
    message: Optional[str] = None


class PushLogCreate(PushLogBase):
    post_id: int


class PushLogRead(PushLogBase):
    id: int
    post_id: int
    created_at: datetime

    class Config:
        from_attributes = True


T = TypeVar("T")


class PaginatedResponse(GenericModel, Generic[T]):
    items: List[T]
    total: int
    skip: int
    limit: int

