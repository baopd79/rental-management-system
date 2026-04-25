"""Request ID middleware — assigns unique ID per request."""

from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.logging import request_id_var


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Inject request_id into context for log correlation."""

    async def dispatch(self, request: Request, call_next):
        # Use client-provided ID if header exists, else generate
        request_id = request.headers.get("x-request-id") or str(uuid4())

        # Set into contextvar for log processors to pick up
        token = request_id_var.set(request_id)
        try:
            response = await call_next(request)
            response.headers["x-request-id"] = request_id
            return response
        finally:
            # Reset contextvar after request
            request_id_var.reset(token)
