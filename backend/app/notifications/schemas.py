"""Notification API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

NotificationAudience = Literal["user", "admin"]
NotificationCategory = Literal["任务", "知识", "系统", "安全"]


class NotificationAction(BaseModel):
    label: str
    to: str


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    audience: NotificationAudience
    category: NotificationCategory
    title: str
    description: str
    read: bool
    created_at: datetime
    action: NotificationAction | None = None


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    unread: int
