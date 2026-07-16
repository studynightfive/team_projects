# 结构化日志配置模块
# 使用 structlog 提供 JSON 格式的结构化日志
# 方案第17.4节：监控必须覆盖日志

import logging
from typing import Any

import structlog


# ============================================================
# 日志处理器配置
# ============================================================
def setup_logging(
    level: str = "INFO",
    json_format: bool = True,
) -> None:
    """
    初始化结构化日志配置

    Args:
        level: 日志级别（DEBUG/INFO/WARNING/ERROR）
        json_format: 是否使用 JSON 格式输出（生产环境应启用）
    """
    # 设置标准库日志级别
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, level.upper(), logging.INFO),
    )

    # 配置 structlog 处理器链
    structlog.configure(
        processors=[
            # 添加日志级别
            structlog.stdlib.add_log_level,
            # 过滤敏感字段（防止 Secret 泄露）
            _filter_sensitive_fields,
            # 添加时间戳
            structlog.processors.TimeStamper(fmt="iso"),
            # 添加调用者信息（文件名和行号，仅 DEBUG 模式）
            structlog.processors.CallsiteParameterAdder(
                {
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.LINENO,
                }
            ) if level.upper() == "DEBUG" else None,
            # 堆栈信息（仅 ERROR 级别）
            structlog.processors.StackInfoRenderer(),
            # 格式化异常信息
            structlog.processors.format_exc_info,
            # 转换为 JSON 或控制台格式
            structlog.dev.ConsoleRenderer()
            if not json_format
            else structlog.processors.JSONRenderer(),
        ],
        # 过滤 None 处理器
        processor_merger=lambda processors: [
            p for p in processors if p is not None
        ],
        # 包装标准库日志
        wrapper_class=structlog.stdlib.BoundLogger,
        # 上下文缓存
        context_class=dict,
        # 日志工厂
        logger_factory=structlog.stdlib.LoggerFactory(),
        # 缓存日志器
        cache_logger_on_first_use=True,
    )


def _filter_sensitive_fields(
    logger: logging.Logger, method_name: str, event_dict: dict
) -> dict:
    """
    过滤敏感字段，防止 Secret 泄露

    以下字段在日志中会被自动替换为 "[REDACTED]"：
    - authorization / auth_header
    - password / password_hash
    - api_key / secret_key / token
    - database_url / redis_url（包含密码）
    """
    sensitive_keys = {
        "authorization",
        "auth_header",
        "password",
        "password_hash",
        "api_key",
        "secret_key",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "database_url",
        "redis_url",
        "cookie",
    }

    for key in list(event_dict.keys()):
        key_lower = key.lower()
        if key_lower in sensitive_keys:
            event_dict[key] = "[REDACTED]"
        # 检查事件字典中的敏感值
        elif isinstance(event_dict[key], str):
            for sensitive in sensitive_keys:
                if sensitive in key_lower:
                    event_dict[key] = "[REDACTED]"
                    break

    return event_dict


# ============================================================
# 安全日志记录辅助函数
# ============================================================
def log_request(
    logger: structlog.BoundLogger,
    request_id: str,
    user_id: str | None,
    action: str,
    result: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    duration_ms: float | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
    **extra: Any,
) -> None:
    """
    记录 API 请求日志（安全格式）

    此函数确保所有日志记录遵循安全规范：
    - 不记录 Authorization 头
    - 不记录密码或密钥
    - 不记录完整请求体或响应体
    - 不记录内部存储路径或 SQL 语句

    Args:
        logger: structlog 日志器
        request_id: 请求唯一标识
        user_id: 当前用户 ID（匿名请求为 None）
        action: 操作类型（如 auth.login, document.upload）
        result: 操作结果（success/failure/denied）
        resource_type: 资源类型（user/document/knowledge_base 等）
        resource_id: 资源 ID
        duration_ms: 请求耗时（毫秒）
        error_code: 错误码（仅失败时）
        error_message: 安全错误信息（仅失败时，不包含堆栈）
        **extra: 额外字段（会经过敏感字段过滤）
    """
    log_data = {
        "request_id": request_id,
        "action": action,
        "result": result,
    }

    if user_id:
        log_data["user_id"] = user_id
    if resource_type:
        log_data["resource_type"] = resource_type
    if resource_id:
        log_data["resource_id"] = resource_id
    if duration_ms is not None:
        log_data["duration_ms"] = duration_ms
    if error_code:
        log_data["error_code"] = error_code
    if error_message:
        log_data["error_message"] = error_message

    log_data.update(extra)

    if result == "failure":
        logger.error("request_failed", **log_data)
    elif result == "denied":
        logger.warning("request_denied", **log_data)
    else:
        logger.info("request_completed", **log_data)
