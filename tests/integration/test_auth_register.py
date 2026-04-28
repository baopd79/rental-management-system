"""Integration tests for POST /api/v1/auth/register."""

from fastapi.testclient import TestClient


class TestRegister:
    """POST /api/v1/auth/register — Landlord registration."""

    URL = "/api/v1/auth/register"

    def test_happy_path(self, client: TestClient) -> None:
        """R1: Valid request returns 201 with access_token + user, no password_hash."""
        response = client.post(
            self.URL,
            json={
                "email": "new@test.com",
                "password": "ValidPass1",
                "full_name": "New User",
            },
        )
        assert response.status_code == 201
        body = response.json()

        # Token shape
        assert "access_token" in body
        assert body["token_type"] == "Bearer"
        assert body["expires_in"] == 3600

        # User shape
        user = body["user"]
        assert user["email"] == "new@test.com"
        assert user["role"] == "landlord"
        assert user["full_name"] == "New User"
        assert user["is_active"] is True
        assert "id" in user

        # Security: NO password_hash leak
        assert "password_hash" not in user

    def test_duplicate_email(self, client: TestClient, landlord_user) -> None:
        """R2: Duplicate email → 409 EMAIL_ALREADY_EXISTS."""
        response = client.post(
            self.URL,
            json={
                "email": landlord_user.email,
                "password": "ValidPass1",
                "full_name": "Dup",
            },
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"

    def test_duplicate_email_case_insensitive(self, client: TestClient, landlord_user) -> None:
        """R3: Email case-insensitive uniqueness — UPPERCASE input matches lowercase DB."""
        response = client.post(
            self.URL,
            json={
                "email": landlord_user.email.upper(),  # uppercase
                "password": "ValidPass1",
                "full_name": "Dup",
            },
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"

    def test_password_no_uppercase(self, client: TestClient) -> None:
        """R4: Password thiếu uppercase → 422."""
        response = client.post(
            self.URL,
            json={"email": "x@y.com", "password": "lowercase1", "full_name": "X"},
        )
        assert response.status_code == 422

    def test_password_no_digit(self, client: TestClient) -> None:
        """R5: Password thiếu digit → 422."""
        response = client.post(
            self.URL,
            json={"email": "x@y.com", "password": "NoDigitPass", "full_name": "X"},
        )
        assert response.status_code == 422

    def test_password_too_short(self, client: TestClient) -> None:
        """R6: Password <8 chars → 422."""
        response = client.post(
            self.URL,
            json={"email": "x@y.com", "password": "Short1", "full_name": "X"},
        )
        assert response.status_code == 422

    def test_invalid_email(self, client: TestClient) -> None:
        """R7: Email format sai → 422."""
        response = client.post(
            self.URL,
            json={"email": "not-an-email", "password": "ValidPass1", "full_name": "X"},
        )
        assert response.status_code == 422
