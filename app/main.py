from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.v1.router import router as api_v1_router
from app.core.config import settings
from app.core.exceptions import RMSException, rms_exception_handler
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    yield


app = FastAPI(
    title="Rental Management System",
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_exception_handler(RMSException, rms_exception_handler)
app.include_router(health_router)
app.include_router(api_v1_router, prefix="/api/v1")
