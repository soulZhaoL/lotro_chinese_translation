# 数据库连接与游标管理。
from contextlib import contextmanager

from psycopg import connect
from psycopg.rows import dict_row

from .config import get_config


def _get_dsn() -> str:
    config = get_config()
    database = config["database"]
    return database["dsn"]


def get_connection():
    return connect(_get_dsn(), row_factory=dict_row)


@contextmanager
def db_cursor():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            yield cursor
            connection.commit()
