# 更新记录接口测试。
from fastapi.testclient import TestClient

from server.app import app
from server.db import db_cursor


def _login(client: TestClient, seed_user):
    response = client.post("/auth/login", json={"username": seed_user["username"], "password": seed_user["password"]})
    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == "0000"
    return payload["data"]["token"]


def test_list_changes_returns_username(seed_user):
    with db_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO text_main (fid, "textId", part, "sourceText", "translatedText", status, "editCount")
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            ("file_changes", 9001, 1, "hello", "旧翻译", 2, 1),
        )
        text_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO text_changes ("textId", "userId", "beforeText", "afterText", reason)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (text_id, seed_user["userId"], "旧翻译", "新翻译", "修正"),
        )

    client = TestClient(app)
    token = _login(client, seed_user)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(f"/changes?id={text_id}", headers=headers)
    assert response.status_code == 200

    items = response.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["userId"] == seed_user["userId"]
    assert items[0]["username"] == seed_user["username"]
