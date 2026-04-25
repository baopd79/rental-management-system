"""Request ID middleware — assigns unique ID per request."""

from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp
from typing import Any
from app.core.logging import request_id_var
from starlette.middleware.base import RequestResponseEndpoint


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Inject request_id into context for log correlation."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,  # RequestResponseEndpoint nếu strict
    ) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid4())
        token = request_id_var.set(request_id)
        try:
            response = await call_next(request)
            response.headers["x-request-id"] = request_id
            return response
        finally:
            request_id_var.reset(token)
