# 认领释放测试。
from fastapi.testclient import TestClient

from server.app import app
from server.db import db_cursor


def _login(client: TestClient, seed_user):
    response = client.post("/auth/login", json={"username": seed_user["username"], "password": seed_user["password"]})
    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == "0000"
    return payload["data"]["token"]


def test_release_claim(seed_user):
    with db_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO text_main (fid, "textId", part, "sourceText", "translatedText", status, "editCount")
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            ("file_a", 1001, 1, "hello", None, 1, 0),
        )
        text_id = cursor.fetchone()["id"]

        cursor.execute(
            """
            INSERT INTO text_claims ("textId", "userId")
            VALUES (%s, %s)
            RETURNING id
            """,
            (text_id, seed_user["userId"]),
        )
        claim_id = cursor.fetchone()["id"]

    client = TestClient(app)
    token = _login(client, seed_user)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.delete(f"/claims/{claim_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["data"]["id"] == claim_id
