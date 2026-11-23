def test_health_reports_process_up(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "ScreenPilot", "version": "0.1.0"}


def test_request_id_is_echoed(client):
    response = client.get("/health", headers={"x-request-id": "req-123"})

    assert response.headers["x-request-id"] == "req-123"


def test_unsafe_request_id_is_replaced(client):
    response = client.get("/health", headers={"x-request-id": "bad id\n"})

    request_id = response.headers["x-request-id"]
    assert request_id != "bad id\n"
    assert "\n" not in request_id


def test_openapi_lists_core_routes(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/health" in paths
    assert "/ready" in paths
    assert "/api/capabilities" in paths
    assert "/api/agent/runs" in paths
    assert "/api/auth/register" in paths
    assert "/api/tasks" in paths
    assert "/api/users/me" in paths
