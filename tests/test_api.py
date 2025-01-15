import pytest
from fastapi.testclient import TestClient

def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "running"}

def test_get_tokens_endpoint(client):
    response = client.get("/tokens")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_websocket_connection(client):
    with client.websocket_connect("/ws") as websocket:
        # Test connection is established
        assert websocket.connected 