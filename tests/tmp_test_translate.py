# 翻译保存测试。
from fastapi.testclient import TestClient

from server.app import app
from server.db import db_cursor


def _login(client: TestClient, seed_user):
    response = client.post("/auth/login", json={"username": seed_user["username"], "password": seed_user["password"]})
    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == "0000"
    return payload["data"]["token"]


def test_translate_update(seed_user):
    with db_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO text_main (fid, "textId", part, "sourceText", "translatedText", status, "editCount")
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            ("file_a", 1001, 1, "hello", "你好", 1, 1),
        )
        text_id = cursor.fetchone()["id"]

    client = TestClient(app)
    token = _login(client, seed_user)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.put(
        f"/texts/{text_id}/translate",
        json={"translatedText": "新的翻译", "reason": "修正"},
        headers=headers,
    )
    assert response.status_code == 200

    with db_cursor() as cursor:
        cursor.execute('SELECT "translatedText", "editCount" FROM text_main WHERE id = %s', (text_id,))
        row = cursor.fetchone()
        assert row["translatedText"] == "新的翻译"
        assert row["editCount"] == 2

        cursor.execute('SELECT COUNT(*) AS total FROM text_changes WHERE "textId" = %s', (text_id,))
        assert cursor.fetchone()["total"] == 1
