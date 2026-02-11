# 文本父子列表与 textId 查询测试。
from fastapi.testclient import TestClient

from server.app import app
from server.db import db_cursor


def _login(client: TestClient, seed_user):
    response = client.post("/auth/login", json={"username": seed_user["username"], "password": seed_user["password"]})
    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == "0000"
    return payload["data"]["token"]


def test_texts_parent_child_and_by_textid(seed_user):
    with db_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO text_main (fid, "textId", part, "sourceText", "translatedText", status, "editCount")
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            ("file_a", 1001, 1, "seg1", None, 1, 0),
        )
        cursor.execute(
            """
            INSERT INTO text_main (fid, "textId", part, "sourceText", "translatedText", status, "editCount")
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            ("file_a", 1002, 2, "seg2", None, 1, 0),
        )
        cursor.execute(
            """
            INSERT INTO text_main (fid, "textId", part, "sourceText", "translatedText", status, "editCount")
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            ("file_a", 1003, 3, "seg3", None, 1, 0),
        )
        cursor.execute(
            """
            INSERT INTO text_main (fid, "textId", part, "sourceText", "translatedText", status, "editCount")
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            ("file_b", 2001, 1, "other", None, 1, 0),
        )

    client = TestClient(app)
    token = _login(client, seed_user)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/texts/parents?fid=file_a", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["part"] == 1

    response = client.get("/texts/children?fid=file_a", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    parts = [item["part"] for item in data["items"]]
    assert parts == sorted(parts)
    assert len(data["items"]) == 3

    response = client.get("/texts/children?fid=file_a&textId=1002", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["textId"] == 1002

    response = client.get("/texts/by-textid?fid=file_a&textId=1002", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["text"]["textId"] == 1002


def test_texts_by_textid_duplicate(seed_user):
    with db_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO text_main (fid, "textId", part, "sourceText", "translatedText", status, "editCount")
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            ("file_dup", 9001, 1, "dup1", None, 1, 0),
        )
        cursor.execute(
            """
            INSERT INTO text_main (fid, "textId", part, "sourceText", "translatedText", status, "editCount")
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            ("file_dup", 9001, 2, "dup2", None, 1, 0),
        )

    client = TestClient(app)
    token = _login(client, seed_user)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/texts/by-textid?fid=file_dup&textId=9001", headers=headers)
    assert response.status_code == 409

    response = client.get("/texts/children?fid=file_dup&textId=9001", headers=headers)
    assert response.status_code == 409
