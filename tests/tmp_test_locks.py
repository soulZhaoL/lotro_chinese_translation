# 锁定接口测试。
from fastapi.testclient import TestClient

from server.app import app
from server.db import db_cursor


def _login(client: TestClient, seed_user):
    response = client.post("/auth/login", json={"username": seed_user["username"], "password": seed_user["password"]})
    assert response.status_code == 200
    return response.json()["token"]


def test_lock_conflict(seed_user):
    with db_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO text_main (fid, text_id, part, source_text, translated_text, status, edit_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            ("file_a", 1001, 1, "hello", None, 1, 0),
        )
        text_id = cursor.fetchone()["id"]

    client = TestClient(app)
    token = _login(client, seed_user)
    headers = {"Authorization": f"Bearer {token}"}

    first = client.post("/locks", json={"text_id": text_id}, headers=headers)
    assert first.status_code == 200

    second = client.post("/locks", json={"text_id": text_id}, headers=headers)
    assert second.status_code == 409
