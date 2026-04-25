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

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup
    # Verify DB connection - fail fast neu DB khong reachable
    with Session(engine) as session:
        session.exec(text("SELECT 1"))

    yield
    # shutdown
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

# Routers
app.include_router(api_router)
app.include_router(health.router)
# chua co routers, viet sau
