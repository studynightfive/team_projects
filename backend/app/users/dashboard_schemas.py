"""业务看板与用户激励响应模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.common.schemas import PaginatedData


class DashboardPeriod(BaseModel):
    days: Literal[7, 30, 90]
    started_at: datetime
    ended_at: datetime


class DashboardScope(BaseModel):
    department_id: str | None = None
    department_name: str


class RateMetric(BaseModel):
    rate: float = Field(ge=0.0, le=100.0)
    numerator: int = Field(ge=0)
    denominator: int = Field(ge=0)


class ResponseTimeMetric(BaseModel):
    average_ms: float = Field(ge=0.0)
    sample_count: int = Field(ge=0)


class DepartmentLeaderboardItem(BaseModel):
    rank: int = Field(ge=1)
    department_id: str
    department_name: str
    points: int = Field(ge=0)
    contribution_count: int = Field(ge=0)
    contributor_count: int = Field(ge=0)


class DashboardMetrics(BaseModel):
    """管理首页真实业务指标，保留旧总量字段以兼容已有客户端。"""

    total_users: int = 0
    active_users: int = 0
    disabled_users: int = 0
    total_roles: int = 0
    total_knowledge_bases: int = 0
    total_documents: int = 0
    total_conversations: int = 0
    total_chats_today: int = 0
    success_rate: float = 0.0
    avg_response_time_ms: float = 0.0
    total_tokens_used: int = 0
    period: DashboardPeriod
    scope: DashboardScope
    knowledge_coverage: RateMetric
    active_searches: int = Field(ge=0)
    effective_answers: int = Field(ge=0)
    unanswered_queries: int = Field(ge=0)
    document_processing: RateMetric
    answer_cache: RateMetric
    response_time: ResponseTimeMetric
    department_leaderboard: PaginatedData[DepartmentLeaderboardItem]


class IncentiveBadge(BaseModel):
    code: str
    name: str
    description: str
    threshold: int = Field(ge=0)
    earned: bool


class IncentiveRule(BaseModel):
    code: str
    name: str
    description: str
    points: int = Field(ge=0)


class ContributionItem(BaseModel):
    id: str
    type: Literal["ready_document"]
    title: str
    points: int = Field(ge=0)
    occurred_at: datetime


class NextBadge(BaseModel):
    code: str
    name: str
    threshold: int = Field(ge=0)
    remaining_points: int = Field(ge=0)


class UserIncentives(BaseModel):
    points: int = Field(ge=0)
    contribution_count: int = Field(ge=0)
    department_rank: int | None = Field(default=None, ge=1)
    department_member_count: int = Field(ge=0)
    badges: list[IncentiveBadge]
    next_badge: NextBadge | None = None
    rules: list[IncentiveRule]
    contributions: PaginatedData[ContributionItem]
