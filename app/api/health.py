# app/api/v1/endpoints/health.py

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlmodel import Session, text

from app.api.deps import get_db
from app.core.config import get_settings

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health", summary="Health check")
def health_check(db: Session = Depends(get_db)) -> JSONResponse:
    """Return app status + DB connectivity. Used by monitoring."""

    # Check DB
    try:
        db.exec(text("SELECT 1"))
        db_status = "ok"
        http_status = status.HTTP_200_OK
        overall = "ok"
    except Exception:
        db_status = "unreachable"
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE
        overall = "degraded"

    return JSONResponse(
        status_code=http_status,
        content={
            "status": overall,
            "version": settings.app_version,
            "environment": settings.app_env,
            "database": db_status,
        },
    )
