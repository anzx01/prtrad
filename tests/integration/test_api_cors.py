from fastapi.testclient import TestClient
import pytest

from services.calibration.service import CalibrationService


@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3111",
    ],
)
def test_health_allows_local_dev_origins(client: TestClient, origin: str):
    response = client.get("/health", headers={"Origin": origin})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-credentials"] == "true"


def test_preflight_allows_json_post_from_local_dev_origin(client: TestClient):
    origin = "http://localhost:3001"
    response = client.options(
        "/backtests/run",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-credentials"] == "true"
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "content-type" in response.headers["access-control-allow-headers"].lower()


def test_health_does_not_allow_external_origin(client: TestClient):
    response = client.get("/health", headers={"Origin": "https://example.com"})

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_server_error_keeps_cors_headers_and_json_body(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    origin = "http://localhost:3001"

    def raise_runtime_error(self, window_type: str = "long"):
        raise RuntimeError(f"forced failure for {window_type}")

    monkeypatch.setattr(CalibrationService, "recompute_all", raise_runtime_error)

    with TestClient(client.app, raise_server_exceptions=False) as error_client:
        response = error_client.post(
            "/calibration/recompute-all?window_type=long",
            headers={"Origin": origin},
        )

    assert response.status_code == 500
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-credentials"] == "true"
    assert response.headers["x-request-id"]

    data = response.json()
    assert data["detail"] == "内部服务异常，请稍后重试。"
    assert data["request_id"] == response.headers["x-request-id"]
