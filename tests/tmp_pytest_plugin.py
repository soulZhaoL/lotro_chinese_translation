# pytest 公共夹具与辅助函数。
import hashlib
import os
from typing import Dict

import pytest

from server.config import get_config
from server.db import db_cursor


@pytest.fixture(scope="session")
def config() -> Dict[str, object]:
    return get_config()


@pytest.fixture(scope="function", autouse=True)
def ensure_tables(config: Dict[str, object]):
    required_tables = [
        "users",
        "roles",
        "user_roles",
        "permissions",
        "role_permissions",
        "text_main",
        "text_claims",
        "text_locks",
        "text_changes",
        "dictionary_entries",
    ]
    with db_cursor() as cursor:
        for table in required_tables:
            cursor.execute("SELECT to_regclass(%s) AS name", (table,))
            row = cursor.fetchone()
            if row is None or row["name"] is None:
                raise RuntimeError(f"缺少数据表: {table}，请先执行迁移")
        cursor.execute("TRUNCATE text_changes, text_locks, text_claims, dictionary_entries, text_main, user_roles, role_permissions, permissions, roles, users RESTART IDENTITY")
    yield


def _hash_password(password: str, salt_hex: str, algorithm: str) -> str:
    salt_bytes = bytes.fromhex(salt_hex)
    hasher = hashlib.new(algorithm)
    hasher.update(salt_bytes)
    hasher.update(password.encode("utf-8"))
    return hasher.hexdigest()


@pytest.fixture(scope="function")
def seed_user(config: Dict[str, object]):
    auth = config["auth"]
    algorithm = auth["hash_algorithm"]
    salt_bytes = auth["salt_bytes"]
    password = "secret123"
    salt_hex = os.urandom(salt_bytes).hex()
    password_hash = _hash_password(password, salt_hex, algorithm)

    with db_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO users (username, password_hash, password_salt, is_guest)
            VALUES (%s, %s, %s, FALSE)
            RETURNING id
            """,
            ("tester", password_hash, salt_hex),
        )
        user_id = cursor.fetchone()["id"]

    return {"username": "tester", "password": password, "user_id": user_id}
