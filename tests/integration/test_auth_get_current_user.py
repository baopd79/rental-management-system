"""Integration tests for GET /api/v1/auth/me — tests get_current_user dependency."""

from fastapi.testclient import TestClient

from app.models.user import User


class TestGetCurrentUser:
    """GET /api/v1/auth/me — Verify get_current_user dependency."""

    URL = "/api/v1/auth/me"

    def test_valid_token(
        self, client: TestClient, landlord_user: User, auth_header
    ) -> None:
        """G1: Valid token → 200 + user info."""
        response = client.get(self.URL, headers=auth_header)
        assert response.status_code == 200
        body = response.json()
        assert body["email"] == landlord_user.email
        assert body["role"] == "landlord"

    def test_missing_token(self, client: TestClient) -> None:
        """G2: No Authorization header → 401 INVALID_TOKEN."""
        response = client.get(self.URL)
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "INVALID_TOKEN"

    def test_garbage_token(self, client: TestClient) -> None:
        """G3: Malformed token → 401 INVALID_TOKEN."""
        response = client.get(
            self.URL,
            headers={"Authorization": "Bearer garbage.token.here"},
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "INVALID_TOKEN"

    def test_inactive_user(
        self, client: TestClient, landlord_user: User, auth_header, db_session
    ) -> None:
        """G4: Token cho user đã bị disable → 401 INVALID_TOKEN."""
        landlord_user.is_active = False
        db_session.add(landlord_user)
        db_session.commit()

        response = client.get(self.URL, headers=auth_header)
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "INVALID_TOKEN"
