# 词典接口测试。
from fastapi.testclient import TestClient

from server.app import app
from server.db import db_cursor


def _login(client: TestClient, seed_user):
    response = client.post("/auth/login", json={"username": seed_user["username"], "password": seed_user["password"]})
    assert response.status_code == 200
    return response.json()["token"]


def test_dictionary_filter(seed_user):
    client = TestClient(app)
    token = _login(client, seed_user)
    headers = {"Authorization": f"Bearer {token}"}

    create = client.post(
        "/dictionary",
        json={"term_key": "orc", "term_value": "兽人", "category": "race"},
        headers=headers,
    )
    assert create.status_code == 200

    response = client.get("/dictionary?keyword=orc", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["term_key"] == "orc"
