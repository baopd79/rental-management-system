# app/api/v1/router.py

"""V1 API router — aggregates all v1 endpoints."""
from fastapi import APIRouter

from app.api import health

api_router = APIRouter(prefix="/api/v1")
