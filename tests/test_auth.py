"""
Auth tests — chạy sau khi Bảo implement security.py + auth_service.py.
"""

import pytest
from fastapi.testclient import TestClient

_REGISTER_URL = "/api/v1/auth/register"
_LOGIN_URL = "/api/v1/auth/login"

_VALID_LANDLORD = {
    "email": "landlord@test.com",
    "password": "Password123",
    "full_name": "Nguyễn Văn A",
}


# ── Register ──────────────────────────────────────────────────────────────────


def test_register_returns_201(client: TestClient) -> None:
    response = client.post(_REGISTER_URL, json=_VALID_LANDLORD)
    assert response.status_code == 201


def test_register_response_shape(client: TestClient) -> None:
    body = client.post(_REGISTER_URL, json=_VALID_LANDLORD).json()
    assert "access_token" in body
    assert body["token_type"] == "Bearer"
    assert "expires_in" in body
    assert body["user"]["email"] == _VALID_LANDLORD["email"]
    assert body["user"]["role"] == "landlord"
    assert body["user"]["is_active"] is True


def test_register_sets_refresh_cookie(client: TestClient) -> None:
    response = client.post(_REGISTER_URL, json=_VALID_LANDLORD)
    assert "refresh_token" in response.cookies


def test_register_duplicate_email_returns_409(client: TestClient) -> None:
    client.post(_REGISTER_URL, json=_VALID_LANDLORD)
    response = client.post(_REGISTER_URL, json=_VALID_LANDLORD)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DUPLICATE_TENANT_EMAIL"


def test_register_weak_password_returns_422(client: TestClient) -> None:
    payload = {**_VALID_LANDLORD, "password": "alllower1"}
    response = client.post(_REGISTER_URL, json=payload)
    assert response.status_code == 422


def test_register_short_password_returns_422(client: TestClient) -> None:
    payload = {**_VALID_LANDLORD, "password": "Ab1"}
    response = client.post(_REGISTER_URL, json=payload)
    assert response.status_code == 422


# ── Login ─────────────────────────────────────────────────────────────────────


@pytest.fixture
def registered_client(client: TestClient) -> TestClient:
    client.post(_REGISTER_URL, json=_VALID_LANDLORD)
    return client


def test_login_returns_200(registered_client: TestClient) -> None:
    response = registered_client.post(
        _LOGIN_URL,
        json={"email": _VALID_LANDLORD["email"], "password": _VALID_LANDLORD["password"]},
    )
    assert response.status_code == 200


def test_login_response_shape(registered_client: TestClient) -> None:
    body = registered_client.post(
        _LOGIN_URL,
        json={"email": _VALID_LANDLORD["email"], "password": _VALID_LANDLORD["password"]},
    ).json()
    assert "access_token" in body
    assert body["user"]["email"] == _VALID_LANDLORD["email"]


def test_login_wrong_password_returns_401(registered_client: TestClient) -> None:
    response = registered_client.post(
        _LOGIN_URL,
        json={"email": _VALID_LANDLORD["email"], "password": "WrongPass999"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_unknown_email_returns_401(client: TestClient) -> None:
    response = client.post(
        _LOGIN_URL,
        json={"email": "nobody@test.com", "password": "Password123"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
