import pytest


def _register(client, email: str) -> dict:
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "valid-passphrase-1",
            "display_name": email.split("@")[0],
        },
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_users_cannot_read_another_users_task(sqlite_app_client):
    client = sqlite_app_client
    alice_tokens = _register(client, "alice@example.com")
    bob_tokens = _register(client, "bob@example.com")

    alice_headers = {"Authorization": f"Bearer {alice_tokens['access_token']}"}
    created = client.post(
        "/api/tasks",
        headers=alice_headers,
        json={"instruction": "Open the quarterly report"},
    )
    assert created.status_code == 201
    task_id = created.json()["id"]

    bob_headers = {"Authorization": f"Bearer {bob_tokens['access_token']}"}
    forbidden = client.get(f"/api/tasks/{task_id}", headers=bob_headers)
    assert forbidden.status_code == 404
    assert forbidden.json()["error"]["code"] == "not_found"


@pytest.mark.asyncio
async def test_agent_run_requires_auth_and_runs_mock_agent(sqlite_app_client):
    client = sqlite_app_client
    unauth = client.post("/api/agent/runs", json={"instruction": "Do something"})
    assert unauth.status_code == 401

    tokens = _register(client, "runner@example.com")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    response = client.post("/api/agent/runs", headers=headers, json={"instruction": "Do something"})
    assert response.status_code == 200
    assert response.json()["outcome"]["status"] == "completed"

    listed = client.get("/api/tasks", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1