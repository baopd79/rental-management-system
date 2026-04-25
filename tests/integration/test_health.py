"""Tests for /health endpoint."""

from fastapi.testclient import TestClient


def test_health_returns_ok_when_db_up(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert "version" in body
    assert "environment" in body


def test_health_response_has_request_id_header(client: TestClient) -> None:
    response = client.get("/health")

    assert "x-request-id" in response.headers


def test_health_preserves_client_request_id(client: TestClient) -> None:
    custom_id = "test-request-id-abc-123"
    response = client.get("/health", headers={"X-Request-ID": custom_id})

    assert response.headers["x-request-id"] == custom_id
