from fastapi import Request
from fastapi.responses import JSONResponse


class RMSException(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


async def rms_exception_handler(request: Request, exc: RMSException) -> JSONResponse:
    request_id = request.headers.get("X-Request-ID", "")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "request_id": request_id,
            }
        },
    )
