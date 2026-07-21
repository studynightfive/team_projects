"""敏感词检查 API 端点

POST /api/v1/sensitive-check
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_any_permission
from app.common.database import get_db
from app.common.models import User
from app.common.schemas import APIResponse, ErrorCode, get_error_message
from app.rag.sensitive_filter.service import check_sensitive

router = APIRouter(prefix="/api/v1", tags=["sensitive-filter"])
logger = structlog.get_logger()


# ============================================================
# Schemas
# ============================================================
class SensitiveCheckRequest(BaseModel):
    """敏感词检查请求"""
    question: str = Field(
        min_length=1,
        max_length=4000,
        description="待检查的问题文本",
    )


class SensitiveCheckResponse(BaseModel):
    """敏感词检查响应"""
    passed: bool = Field(description="是否通过检查")
    verdict: str = Field(description="过滤判定: pass / regex / bert")
    reason: str = Field(default="", description="拦截原因（仅 blocked 时有值）")
    regex_matches: list[str] = Field(
        default_factory=list,
        description="Layer 1 正则匹配结果",
    )
    bert_confidence: float = Field(
        default=0.0,
        description="Layer 2 BERT 置信度 (0.0-1.0)",
    )
    bert_label: str = Field(default="", description="BERT 匹配的敏感意图标签")


# ============================================================
# 路由
# ============================================================
@router.post(
    "/sensitive-check",
    response_model=APIResponse[SensitiveCheckResponse],
    summary="敏感词检查",
    description=(
        "对用户输入的问题进行两层敏感词过滤：\n"
        "- Layer 1: 正则表达式精确匹配已知敏感词和攻击模式\n"
        "- Layer 2: BERT 语义理解和意图识别\n"
        "返回是否通过及详细的过滤信息。"
    ),
)
async def sensitive_check_endpoint(
    request: Request,
    payload: SensitiveCheckRequest,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_any_permission("chat.use", "chat:write")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """敏感词检查 API

    前端在用户点击"发送"时调用此接口进行预检。
    如果返回 passed=false，前端弹出警告阻止发送。
    """
    logger.info(
        "sensitive_check_request",
        user_id=user.id,
        question_len=len(payload.question),
    )

    result = await check_sensitive(payload.question)

    if result.passed:
        code = ErrorCode.SUCCESS
        message = "检查通过"
    else:
        code = ErrorCode.SENSITIVE_CONTENT
        message = get_error_message(ErrorCode.SENSITIVE_CONTENT)

    return APIResponse(
        code=code,
        message=message,
        data=SensitiveCheckResponse(
            passed=result.passed,
            verdict=result.verdict.value,
            reason=result.reason,
            regex_matches=result.regex_matches,
            bert_confidence=result.bert_confidence,
            bert_label=result.bert_label,
        ).model_dump(),
        request_id=getattr(request.state, "request_id", ""),
    ).model_dump()
