# 审计日志请求/响应模型
# 员工3 负责
# 对应 OpenAPI：GET /audit-logs

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    """审计日志响应"""

    id: str
    user_id: str | None = None
    username: str | None = None
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    detail: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    result: str
    request_id: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
