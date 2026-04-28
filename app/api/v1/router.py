# app/api/v1/router.py

"""V1 API router — aggregates all v1 endpoints."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
