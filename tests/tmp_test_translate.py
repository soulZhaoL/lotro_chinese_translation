# 翻译保存测试。
from fastapi.testclient import TestClient

from server.app import app
from server.db import db_cursor


def _login(client: TestClient, seed_user):
    response = client.post("/auth/login", json={"username": seed_user["username"], "password": seed_user["password"]})
    assert response.status_code == 200
    return response.json()["token"]


def test_translate_update(seed_user):
    with db_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO text_main (fid, part, source_text, translated_text, status, edit_count)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            ("file_a", "p1", "hello", "你好", "待认领", 1),
        )
        text_id = cursor.fetchone()["id"]

    client = TestClient(app)
    token = _login(client, seed_user)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.put(
        f"/texts/{text_id}/translate",
        json={"translated_text": "新的翻译", "reason": "修正"},
        headers=headers,
    )
    assert response.status_code == 200

    with db_cursor() as cursor:
        cursor.execute("SELECT translated_text, edit_count FROM text_main WHERE id = %s", (text_id,))
        row = cursor.fetchone()
        assert row["translated_text"] == "新的翻译"
        assert row["edit_count"] == 2

        cursor.execute("SELECT COUNT(*) AS total FROM text_changes WHERE text_id = %s", (text_id,))
        assert cursor.fetchone()["total"] == 1
