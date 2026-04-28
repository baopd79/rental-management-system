# tests/integration/test_db_isolation.py
"""Verify SAVEPOINT pattern: tests don't leak data."""

from app.core.enums import UserRole
from app.core.security import hash_password
from app.repositories.user_repo import UserRepo


def test_create_user_step1(db_session):
    """Step 1: create user — service layer commits, but rollback at fixture cleanup."""
    repo = UserRepo(db_session)
    repo.create(
        email="leak-test@example.com",
        password_hash=hash_password("Password1"),
        full_name="Leak Test",
        role=UserRole.LANDLORD,
    )
    # Verify visible within same test
    found = repo.get_by_email("leak-test@example.com")
    assert found is not None


def test_no_leak_step2(db_session):
    """Step 2: previous test's user must NOT exist (rollback worked)."""
    repo = UserRepo(db_session)
    user = repo.get_by_email("leak-test@example.com")
    assert user is None, (
        "Test isolation broken: user from previous test still exists. "
        "SAVEPOINT pattern not working."
    )
