# 词典接口测试。
from fastapi.testclient import TestClient

from server.app import app


def _login(client: TestClient, seed_user):
    response = client.post("/auth/login", json={"username": seed_user["username"], "password": seed_user["password"]})
    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == "0000"
    return payload["data"]["token"]


def test_dictionary_filter(seed_user):
    client = TestClient(app)
    token = _login(client, seed_user)
    headers = {"Authorization": f"Bearer {token}"}

    create = client.post(
        "/dictionary",
        json={"termKey": "orc", "termValue": "兽人", "category": "race"},
        headers=headers,
    )
    assert create.status_code == 200

    response = client.get("/dictionary?keyword=orc", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["termKey"] == "orc"
