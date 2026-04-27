from typing import ClassVar

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.logging import request_id_var


class RMSException(Exception):
    """Base for all domain exceptions."""

    code: ClassVar[str] = "INTERNAL_ERROR"
    status_code: ClassVar[int] = 500
    default_message: ClassVar[str] = "An unexpected error occurred"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


class AuthError(RMSException):
    """Base for authentication errors."""

    pass  # not raised directly, just categorization


class InvalidCredentialsError(AuthError):
    code: ClassVar[str] = "INVALID_CREDENTIALS"
    status_code: ClassVar[int] = 401
    default_message: ClassVar[str] = "Invalid email or password"


class InvalidTokenError(AuthError):
    code: ClassVar[str] = "INVALID_TOKEN"
    status_code: ClassVar[int] = 401
    default_message: ClassVar[str] = "Invalid authentication token"


class TokenExpiredError(AuthError):
    code: ClassVar[str] = "TOKEN_EXPIRED"
    status_code: ClassVar[int] = 401
    default_message: ClassVar[str] = "Authentication token has expired"


class EmailAlreadyExistsError(RMSException):
    code: ClassVar[str] = "EMAIL_ALREADY_EXISTS"
    status_code: ClassVar[int] = 409
    default_message: ClassVar[str] = "Email already registered"


class NotFoundError(RMSException):
    code: ClassVar[str] = "NOT_FOUND"
    status_code: ClassVar[int] = 404
    default_message: ClassVar[str] = "Resource not found"


class PermissionDeniedError(RMSException):
    code: ClassVar[str] = "PERMISSION_DENIED"
    status_code: ClassVar[int] = 403
    default_message: ClassVar[str] = "Insufficient permissions"


async def rms_exception_handler(
    request: Request,
    exc: RMSException,
) -> JSONResponse:
    """Map domain exception → JSON error response."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "request_id": request_id_var.get(),  # None nếu chưa set
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers. Call from main.py."""
    app.add_exception_handler(RMSException, rms_exception_handler)  # type: ignore[arg-type]
