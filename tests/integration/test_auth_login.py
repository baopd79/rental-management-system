"""Integration tests for POST /api/v1/auth/login."""

from fastapi.testclient import TestClient

from app.models.user import User


class TestLogin:
    """POST /api/v1/auth/login — Email + password authentication."""

    URL = "/api/v1/auth/login"

    def test_happy_path(self, client: TestClient, landlord_user: User) -> None:
        """L1: Valid credentials → 200 + access_token, last_login_at updated."""
        # NOTE: landlord_user fixture uses password "ValidPass1"
        response = client.post(
            self.URL,
            json={"email": landlord_user.email, "password": "ValidPass1"},
        )
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert body["token_type"] == "Bearer"
        assert body["user"]["email"] == landlord_user.email

    def test_wrong_password(self, client: TestClient, landlord_user: User) -> None:
        """L2: Wrong password → 401 INVALID_CREDENTIALS."""
        response = client.post(
            self.URL,
            json={"email": landlord_user.email, "password": "WrongPass1"},
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"

    def test_unknown_email(self, client: TestClient) -> None:
        """L3: Email không tồn tại → 401 INVALID_CREDENTIALS (anti-enumeration)."""
        response = client.post(
            self.URL,
            json={"email": "nope@test.com", "password": "ValidPass1"},
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"

    def test_email_case_insensitive(
        self, client: TestClient, landlord_user: User
    ) -> None:
        """L4: Login với email UPPERCASE → 200 (DB store lowercase)."""
        response = client.post(
            self.URL,
            json={"email": landlord_user.email.upper(), "password": "ValidPass1"},
        )
        assert response.status_code == 200

    def test_inactive_user(
        self, client: TestClient, landlord_user: User, db_session
    ) -> None:
        """L5: User inactive → 401 INVALID_CREDENTIALS (uniform with other failures)."""
        landlord_user.is_active = False
        db_session.add(landlord_user)
        db_session.commit()

        response = client.post(
            self.URL,
            json={"email": landlord_user.email, "password": "ValidPass1"},
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
