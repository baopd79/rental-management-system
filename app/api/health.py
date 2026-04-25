import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlmodel import Session

from app.core.config import settings
from app.db.session import get_session

router = APIRouter(tags=["Ops"])
logger = structlog.get_logger()


@router.get("/health")
def health_check(session: Session = Depends(get_session)) -> dict:
    try:
        session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        logger.warning("health_check.db_unreachable")
        db_status = "error"

    return {"status": "ok", "version": settings.app_version, "db": db_status}
