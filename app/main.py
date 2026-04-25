"""FastAPI application entry point
Wires togeter:
-app lifespan(startup/shutdown)
-middleware(CORS,...)
-API routers
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, text

from app.core.config import get_settings
from app.db.session import engine
from app.api.v1.router import api_router
from app.api import health
from app.core.logging import configure_logging, get_logger
from app.middleware.request_id import RequestIDMiddleware

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging()  # ← Add this FIRST
    log = get_logger(__name__)
    log.info("app_starting", version=settings.app_version, env=settings.app_env)

    with Session(engine) as session:
        session.exec(text("SELECT 1"))

    log.info("app_started")
    yield

    log.info("app_shutting_down")
    engine.dispose()


app = FastAPI(title="RMS API", version=settings.app_version, lifespan=lifespan)


# Middleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIDMiddleware)
# Routers
app.include_router(api_router)
app.include_router(health.router)
# chua co routers, viet sau
