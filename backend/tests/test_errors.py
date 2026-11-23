def test_unknown_path_uses_error_envelope(client):
    response = client.get("/missing")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "http_error"
    assert isinstance(body["error"]["message"], str)
