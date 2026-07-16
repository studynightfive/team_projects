# 统一响应和错误码定义
# 员工3 负责
# 方案第14.2节：统一响应格式
# 方案第14.3节：错误码范围

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

# ============================================================
# 泛型类型变量
# ============================================================
T = TypeVar("T")


# ============================================================
# 统一响应模型
# ============================================================
class APIResponse(BaseModel, Generic[T]):
    """统一 API 响应格式（方案第14.2节）

    ```json
    {
      "code": 0,
      "message": "success",
      "data": {},
      "request_id": "uuid"
    }
    ```
    """

    code: int = 0
    message: str = "success"
    data: T | None = None
    request_id: str = ""


class PaginatedData(BaseModel, Generic[T]):
    """分页数据结构"""

    items: list[T]
    page: int
    page_size: int
    total: int


# ============================================================
# 错误码定义（方案第14.3节）
# ============================================================
class ErrorCode:
    """统一错误码"""

    # ---- 通用错误 (10000–10999) ----
    SUCCESS = 0
    INTERNAL_ERROR = 10000
    VALIDATION_ERROR = 10001
    NOT_FOUND = 10002
    METHOD_NOT_ALLOWED = 10003
    RATE_LIMIT_EXCEEDED = 10004

    # ---- 认证和权限 (11000–11999) ----
    UNAUTHORIZED = 11000
    INVALID_CREDENTIALS = 11001
    TOKEN_EXPIRED = 11002
    TOKEN_INVALID = 11003
    TOKEN_REVOKED = 11004
    FORBIDDEN = 11005
    USER_DISABLED = 11006
    PASSWORD_RESET_REQUIRED = 11007
    SESSION_REVOKED = 11008

    # ---- 用户和角色 (12000–12999) ----
    USER_NOT_FOUND = 12000
    USER_ALREADY_EXISTS = 12001
    INVALID_USER_STATUS = 12002
    ROLE_NOT_FOUND = 12003
    ROLE_ALREADY_EXISTS = 12004
    PERMISSION_NOT_FOUND = 12005
    INVALID_ROLE_STATUS = 12006

    # ---- 知识库和文档 (13000–13999) ----
    KB_NOT_FOUND = 13000
    KB_ACCESS_DENIED = 13001
    DOCUMENT_NOT_FOUND = 13002

    # ---- 转换和 OCR (14000–14999) ----
    CONVERSION_FAILED = 14000
    OCR_FAILED = 14001

    # ---- 检索和问答 (15000–15999) ----
    SEARCH_FAILED = 15000
    CHAT_FAILED = 15001

    # ---- 导出和下载 (16000–16999) ----
    EXPORT_FAILED = 16000
    DOWNLOAD_EXPIRED = 16001

    # ---- 评测和运维 (17000–17999) ----
    METRICS_UNAVAILABLE = 17000


# ============================================================
# 错误消息映射
# ============================================================
ERROR_MESSAGES: dict[int, str] = {
    ErrorCode.SUCCESS: "成功",
    ErrorCode.INTERNAL_ERROR: "服务器内部错误",
    ErrorCode.VALIDATION_ERROR: "请求参数错误",
    ErrorCode.NOT_FOUND: "资源不存在",
    ErrorCode.METHOD_NOT_ALLOWED: "请求方法不允许",
    ErrorCode.RATE_LIMIT_EXCEEDED: "请求过于频繁，请稍后重试",
    ErrorCode.UNAUTHORIZED: "未登录或登录已过期",
    ErrorCode.INVALID_CREDENTIALS: "用户名或密码错误",
    ErrorCode.TOKEN_EXPIRED: "登录已过期，请重新登录",
    ErrorCode.TOKEN_INVALID: "Token 无效",
    ErrorCode.TOKEN_REVOKED: "Token 已被撤销",
    ErrorCode.FORBIDDEN: "无权限访问",
    ErrorCode.USER_DISABLED: "用户已被禁用",
    ErrorCode.PASSWORD_RESET_REQUIRED: "需要重置密码",
    ErrorCode.SESSION_REVOKED: "会话已被撤销",
    ErrorCode.USER_NOT_FOUND: "用户不存在",
    ErrorCode.USER_ALREADY_EXISTS: "用户名已存在",
    ErrorCode.INVALID_USER_STATUS: "用户状态无效",
    ErrorCode.ROLE_NOT_FOUND: "角色不存在",
    ErrorCode.ROLE_ALREADY_EXISTS: "角色名已存在",
    ErrorCode.PERMISSION_NOT_FOUND: "权限不存在",
    ErrorCode.INVALID_ROLE_STATUS: "角色状态无效",
    ErrorCode.KB_NOT_FOUND: "知识库不存在",
    ErrorCode.KB_ACCESS_DENIED: "无权访问该知识库",
    ErrorCode.DOCUMENT_NOT_FOUND: "文档不存在",
    ErrorCode.CONVERSION_FAILED: "文档转换失败",
    ErrorCode.OCR_FAILED: "OCR 识别失败",
    ErrorCode.SEARCH_FAILED: "检索失败",
    ErrorCode.CHAT_FAILED: "问答失败",
    ErrorCode.EXPORT_FAILED: "导出失败",
    ErrorCode.DOWNLOAD_EXPIRED: "下载链接已过期",
    ErrorCode.METRICS_UNAVAILABLE: "指标数据不可用",
}


def get_error_message(code: int) -> str:
    """获取错误码对应的消息"""
    return ERROR_MESSAGES.get(code, "未知错误")
