# 自定义业务异常
# 员工3 负责
# 用于在服务层抛出业务异常，由全局异常处理器转换为统一响应格式

from app.common.schemas import ErrorCode, get_error_message


class AppException(Exception):  # noqa: N818
    """应用基础异常

    所有业务异常继承此类，由全局异常处理器捕获并返回统一格式。
    """

    def __init__(
        self,
        code: int | None = None,
        message: str | None = None,
        status_code: int = 400,
        request_id: str = "",
        detail: str | None = None,
    ) -> None:
        self.code = code if code is not None else ErrorCode.INTERNAL_ERROR
        self.message = message or get_error_message(self.code)
        self.status_code = status_code
        self.request_id = request_id
        self.detail = detail
        super().__init__(self.message)


# ============================================================
# 认证异常 (11000–11999)
# ============================================================
class UnauthorizedException(AppException):
    """未认证（401）"""

    def __init__(self, message: str | None = None, request_id: str = "") -> None:
        super().__init__(
            code=ErrorCode.UNAUTHORIZED,
            message=message or get_error_message(ErrorCode.UNAUTHORIZED),
            status_code=401,
            request_id=request_id,
        )


class InvalidCredentialsException(AppException):
    """用户名或密码错误（401）"""

    def __init__(self, request_id: str = "") -> None:
        super().__init__(
            code=ErrorCode.INVALID_CREDENTIALS,
            status_code=401,
            request_id=request_id,
        )


class TokenExpiredException(AppException):
    """Token 过期（401）"""

    def __init__(self, request_id: str = "") -> None:
        super().__init__(
            code=ErrorCode.TOKEN_EXPIRED,
            status_code=401,
            request_id=request_id,
        )


class TokenInvalidException(AppException):
    """Token 无效（401）"""

    def __init__(self, request_id: str = "") -> None:
        super().__init__(
            code=ErrorCode.TOKEN_INVALID,
            status_code=401,
            request_id=request_id,
        )


class ForbiddenException(AppException):
    """无权限（403）"""

    def __init__(self, message: str | None = None, request_id: str = "") -> None:
        super().__init__(
            code=ErrorCode.FORBIDDEN,
            message=message or get_error_message(ErrorCode.FORBIDDEN),
            status_code=403,
            request_id=request_id,
        )


class UserDisabledException(AppException):
    """用户被禁用（403）"""

    def __init__(self, request_id: str = "") -> None:
        super().__init__(
            code=ErrorCode.USER_DISABLED,
            status_code=403,
            request_id=request_id,
        )


# ============================================================
# 用户和角色异常 (12000–12999)
# ============================================================
class NotFoundException(AppException):
    """资源不存在（404）"""

    def __init__(
        self,
        code: int = ErrorCode.NOT_FOUND,
        message: str | None = None,
        request_id: str = "",
    ) -> None:
        super().__init__(
            code=code,
            message=message or get_error_message(code),
            status_code=404,
            request_id=request_id,
        )


class ConflictException(AppException):
    """资源冲突（409）"""

    def __init__(
        self,
        code: int,
        message: str | None = None,
        request_id: str = "",
    ) -> None:
        super().__init__(
            code=code,
            message=message or get_error_message(code),
            status_code=409,
            request_id=request_id,
        )


# ============================================================
# 校验异常 (422)
# ============================================================
class ValidationException(AppException):
    """请求参数校验失败（422）"""

    def __init__(self, message: str = "请求参数错误", request_id: str = "") -> None:
        super().__init__(
            code=ErrorCode.VALIDATION_ERROR,
            message=message,
            status_code=422,
            request_id=request_id,
        )


class SensitiveContentException(AppException):
    """问题包含敏感内容（422）—— 敏感词过滤拦截"""

    def __init__(
        self,
        message: str | None = None,
        request_id: str = "",
        detail: str | None = None,
    ) -> None:
        super().__init__(
            code=ErrorCode.SENSITIVE_CONTENT,
            message=message or "问题包含敏感内容，请修改后重新提问",
            status_code=422,
            request_id=request_id,
            detail=detail,
        )
