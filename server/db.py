# 数据库连接与游标管理。
from contextlib import contextmanager
from typing import Any, Dict
from urllib.parse import parse_qs, unquote, urlparse

import pymysql
from pymysql.constants import FIELD_TYPE
from pymysql.converters import conversions
from pymysql.cursors import DictCursor, SSDictCursor

from .config import get_config


class DatabaseConfigError(Exception):
    pass


def _get_dsn() -> str:
    config = get_config()
    database = config["database"]
    return database["dsn"]


def _parse_mysql_dsn(dsn: str) -> Dict[str, Any]:
    parsed = urlparse(dsn)
    if parsed.scheme not in {"mysql", "mysql+pymysql"}:
        raise DatabaseConfigError("database.dsn 必须使用 mysql:// 或 mysql+pymysql://")
    if parsed.username is None or parsed.username == "":
        raise DatabaseConfigError("database.dsn 缺少用户名")
    if parsed.password is None:
        raise DatabaseConfigError("database.dsn 缺少密码")
    if parsed.hostname is None or parsed.hostname == "":
        raise DatabaseConfigError("database.dsn 缺少主机名")
    if parsed.port is None:
        raise DatabaseConfigError("database.dsn 缺少端口")

    database_name = parsed.path.lstrip("/")
    if database_name == "":
        raise DatabaseConfigError("database.dsn 缺少数据库名")

    query = parse_qs(parsed.query, keep_blank_values=True)
    if "charset" not in query or len(query["charset"]) != 1 or query["charset"][0] == "":
        raise DatabaseConfigError("database.dsn 缺少 charset 参数")

    return {
        "host": parsed.hostname,
        "port": parsed.port,
        "user": unquote(parsed.username),
        "password": unquote(parsed.password),
        "database": database_name,
        "charset": query["charset"][0],
    }


def _tinyint_to_bool(value: Any) -> Any:
    if value is None:
        return None
    return value == b"1"


def _build_mysql_converters():
    converted = conversions.copy()
    converted[FIELD_TYPE.TINY] = _tinyint_to_bool
    return converted


def get_connection():
    dsn = _get_dsn()
    mysql = _parse_mysql_dsn(dsn)
    return pymysql.connect(
        host=mysql["host"],
        port=mysql["port"],
        user=mysql["user"],
        password=mysql["password"],
        database=mysql["database"],
        charset=mysql["charset"],
        cursorclass=DictCursor,
        conv=_build_mysql_converters(),
        init_command="SET SESSION sql_mode = CONCAT_WS(',', @@SESSION.sql_mode, 'ANSI_QUOTES')",
        autocommit=False,
    )


@contextmanager
def db_cursor():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            yield cursor
            connection.commit()


@contextmanager
def db_stream_cursor():
    with get_connection() as connection:
        with connection.cursor(SSDictCursor) as cursor:
            yield cursor
            connection.commit()
