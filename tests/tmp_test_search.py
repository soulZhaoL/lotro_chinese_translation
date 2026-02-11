# 搜索与分页测试。
from fastapi.testclient import TestClient

from server.app import app
from server.db import db_cursor


def _login(client: TestClient, seed_user):
    response = client.post("/auth/login", json={"username": seed_user["username"], "password": seed_user["password"]})
    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == "0000"
    return payload["data"]["token"]


def test_keyword_search(seed_user):
    with db_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO text_main (fid, "textId", part, "sourceText", "translatedText", status, "editCount")
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            ("file_a", 1001, 1, "hello world", None, 1, 0),
        )
        cursor.execute(
            """
            INSERT INTO text_main (fid, "textId", part, "sourceText", "translatedText", status, "editCount")
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            ("file_b", 2002, 1, "other content", None, 1, 0),
        )

    client = TestClient(app)
    token = _login(client, seed_user)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/texts/parents?sourceKeyword=hello", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["fid"] == "file_a"
