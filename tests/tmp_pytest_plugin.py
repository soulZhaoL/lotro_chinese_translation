# pytest 公共夹具与辅助函数。
import hashlib
import os
from typing import Dict

import pytest

from server.config import get_config
from server.db import db_cursor


def pytest_addoption(parser):
    parser.addoption(
        "--run-db-tests",
        action="store_true",
        default=False,
        help="启用需要数据库连接的集成测试（需确保 SSH 隧道/数据库可用）",
    )


@pytest.fixture(scope="session")
def config() -> Dict[str, object]:
    return get_config()


@pytest.fixture(scope="function", autouse=True)
def ensure_tables(config: Dict[str, object], request):
    # 标记为 no_db 的测试不依赖数据库，允许在无隧道/无数据库时执行。
    if request.node.get_closest_marker("no_db") is not None:
        yield
        return

    # 维护模式用例不依赖数据库，避免本地无 DB 时被夹具阻断。
    if request.node.fspath.basename == "test_maintenance.py":
        yield
        return

    if not bool(request.config.getoption("--run-db-tests")):
        pytest.skip("未启用数据库集成测试，请使用 --run-db-tests 并确保 SSH 隧道可用")

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
            cursor.execute(
                """
                SELECT COUNT(*) AS cnt
                FROM information_schema.tables
                WHERE table_schema = DATABASE() AND table_name = %s
                """,
                (table,),
            )
            row = cursor.fetchone()
            if row is None or row["cnt"] == 0:
                raise RuntimeError(f"缺少数据表: {table}，请先执行迁移")
        for table in required_tables:
            cursor.execute(f"TRUNCATE TABLE {table}")
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
            INSERT INTO users (username, "passwordHash", "passwordSalt", "isGuest")
            VALUES (%s, %s, %s, FALSE)
            """,
            ("tester", password_hash, salt_hex),
        )
        user_id = cursor.lastrowid

    return {"username": "tester", "password": password, "userId": user_id}
