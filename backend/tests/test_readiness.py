def test_ready_reports_closed_dependencies(client):
    response = client.get("/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["checks"]["database"]["status"] == "down"
    assert body["checks"]["redis"]["status"] == "down"
    assert "screenpilot:" not in response.text
    assert "postgresql+asyncpg://" not in response.text
    assert "redis://" not in response.text
