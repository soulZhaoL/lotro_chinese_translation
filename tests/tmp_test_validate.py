# 校验接口测试。
from fastapi.testclient import TestClient

from server.app import app
from server.db import db_cursor


def _login(client: TestClient, seed_user):
    response = client.post("/auth/login", json={"username": seed_user["username"], "password": seed_user["password"]})
    assert response.status_code == 200
    return response.json()["token"]


def test_validate_text(seed_user):
    with db_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO text_main (fid, part, source_text, translated_text, status, edit_count)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            ("file_a", "p1", "Hello {name} %s", None, "待认领", 0),
        )
        text_id = cursor.fetchone()["id"]

    client = TestClient(app)
    token = _login(client, seed_user)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/validate",
        json={"text_id": text_id, "translated_text": "你好 {name} %s"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["errors"] == []
