"""Unit tests for common schemas, error codes, and exceptions."""
import pytest

from app.common.exceptions import (
    AppException,
    ConflictException,
    ForbiddenException,
    InvalidCredentialsException,
    NotFoundException,
    TokenExpiredException,
    TokenInvalidException,
    UnauthorizedException,
    UserDisabledException,
    ValidationException,
)
from app.common.schemas import (
    APIResponse,
    ErrorCode,
    PaginatedData,
    get_error_message,
)


class TestAPIResponse:
    """Test unified API response model."""

    def test_default_response(self):
        """Default response has code=0, message='success'."""
        resp = APIResponse()
        assert resp.code == 0
        assert resp.message == "success"
        assert resp.data is None

    def test_response_with_data(self):
        """Response can carry typed data."""
        resp = APIResponse[str](code=0, message="ok", data="hello")
        assert resp.data == "hello"

    def test_response_with_request_id(self):
        """Response carries request_id."""
        resp = APIResponse(request_id="abc-123")
        assert resp.request_id == "abc-123"

    def test_paginated_data(self):
        """PaginatedData wraps items with page info."""
        data = PaginatedData[str](
            items=["a", "b"], page=1, page_size=20, total=100
        )
        assert len(data.items) == 2
        assert data.total == 100


class TestErrorCodes:
    """Test error code definitions."""

    def test_success_code_is_zero(self):
        """Success code is 0."""
        assert ErrorCode.SUCCESS == 0

    def test_internal_error_code(self):
        """Internal error code is 10000."""
        assert ErrorCode.INTERNAL_ERROR == 10000

    def test_unauthorized_code(self):
        """Unauthorized code is 11000."""
        assert ErrorCode.UNAUTHORIZED == 11000

    def test_forbidden_code(self):
        """Forbidden code is 11005."""
        assert ErrorCode.FORBIDDEN == 11005

    def test_get_error_message_known(self):
        """Known error codes return Chinese messages."""
        msg = get_error_message(ErrorCode.UNAUTHORIZED)
        assert "登录" in msg

    def test_get_error_message_unknown(self):
        """Unknown error codes return fallback."""
        msg = get_error_message(99999)
        assert msg == "未知错误"

    def test_all_defined_codes_have_messages(self):
        """Every error code defined in ErrorCode has a message."""
        for name in dir(ErrorCode):
            if name.startswith("_"):
                continue
            code = getattr(ErrorCode, name)
            if isinstance(code, int):
                msg = get_error_message(code)
                assert msg, f"ErrorCode.{name} ({code}) has no message"


class TestAppExceptions:
    """Test custom exception classes."""

    def test_app_exception_default_status(self):
        """Default AppException has status 400."""
        exc = AppException(code=ErrorCode.VALIDATION_ERROR)
        assert exc.code == ErrorCode.VALIDATION_ERROR
        assert exc.status_code == 400

    def test_unauthorized_exception(self):
        """UnauthorizedException has status 401."""
        exc = UnauthorizedException()
        assert exc.status_code == 401
        assert exc.code == ErrorCode.UNAUTHORIZED

    def test_forbidden_exception(self):
        """ForbiddenException has status 403."""
        exc = ForbiddenException()
        assert exc.status_code == 403
        assert exc.code == ErrorCode.FORBIDDEN

    def test_not_found_exception(self):
        """NotFoundException has status 404."""
        exc = NotFoundException()
        assert exc.status_code == 404

    def test_conflict_exception(self):
        """ConflictException has status 409."""
        exc = ConflictException(code=ErrorCode.USER_ALREADY_EXISTS)
        assert exc.status_code == 409

    def test_validation_exception(self):
        """ValidationException has status 422."""
        exc = ValidationException()
        assert exc.status_code == 422

    def test_exception_is_exception_subclass(self):
        """All app exceptions are Exception subclasses."""
        assert isinstance(AppException(), Exception)
        assert isinstance(UnauthorizedException(), AppException)
        assert isinstance(InvalidCredentialsException(), AppException)
        assert isinstance(TokenExpiredException(), AppException)
        assert isinstance(TokenInvalidException(), AppException)
        assert isinstance(ForbiddenException(), AppException)
        assert isinstance(UserDisabledException(), AppException)
        assert isinstance(NotFoundException(), AppException)
        assert isinstance(ConflictException(code=ErrorCode.USER_ALREADY_EXISTS), AppException)
        assert isinstance(ValidationException(), AppException)

    def test_exception_custom_message(self):
        """Custom message overrides default."""
        exc = UnauthorizedException(message="Custom message")
        assert exc.message == "Custom message"

    def test_exception_with_request_id(self):
        """Exception carries request_id."""
        exc = ForbiddenException(request_id="req-123")
        assert exc.request_id == "req-123"
