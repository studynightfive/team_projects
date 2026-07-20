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

    # 构建处理器链
    processors: list[Any] = [
        structlog.stdlib.add_log_level,
        _filter_sensitive_fields,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # DEBUG 模式添加调用者信息
    if level.upper() == "DEBUG":
        processors.append(
            structlog.processors.CallsiteParameterAdder(
                {
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.LINENO,
                }
            )
        )

    # 输出格式：JSON 或控制台
    if json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _filter_sensitive_fields(
    _logger: logging.Logger,
    _method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
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

    不记录：Authorization 头、密码、密钥、完整请求体、内部路径、SQL 语句
    """
    log_data: dict[str, Any] = {
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
