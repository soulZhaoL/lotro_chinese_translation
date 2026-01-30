# 搜索与分页测试。
from fastapi.testclient import TestClient

from server.app import app
from server.db import db_cursor


def _login(client: TestClient, seed_user):
    response = client.post("/auth/login", json={"username": seed_user["username"], "password": seed_user["password"]})
    assert response.status_code == 200
    return response.json()["token"]


def test_keyword_search(seed_user):
    with db_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO text_main (fid, part, source_text, translated_text, status, edit_count)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            ("file_a", "p1", "hello world", None, "待认领", 0),
        )
        cursor.execute(
            """
            INSERT INTO text_main (fid, part, source_text, translated_text, status, edit_count)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            ("file_b", "p2", "other content", None, "待认领", 0),
        )

    client = TestClient(app)
    token = _login(client, seed_user)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/texts?keyword=hello", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["fid"] == "file_a"
