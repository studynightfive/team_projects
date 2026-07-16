# 系统概览响应模型
# 员工3 负责
# 提供管理仪表板需要的聚合数据

from pydantic import BaseModel


class DashboardMetrics(BaseModel):
    """系统概览指标"""

    total_users: int = 0
    active_users: int = 0
    disabled_users: int = 0
    total_roles: int = 0
    total_knowledge_bases: int = 0
    total_documents: int = 0
    total_conversations: int = 0
    # 以下指标依赖其他模块，在对应模块就位后补充
    total_chats_today: int = 0
    success_rate: float = 0.0
    avg_response_time_ms: float = 0.0
    total_tokens_used: int = 0
