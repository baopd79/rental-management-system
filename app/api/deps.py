# app/api/deps.py

"""Common FastAPI dependencies."""
from app.db.session import get_db

__all__ = ["get_db"]
