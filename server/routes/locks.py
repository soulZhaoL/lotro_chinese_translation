# 锁定与释放相关路由。
from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..config import get_config
from ..db import db_cursor
from ..response import success_response
from .deps import require_auth

router = APIRouter(prefix="/locks", tags=["locks"])


class LockRequest(BaseModel):
    text_id: int


def _utc_now() -> datetime:
    return datetime.utcnow()


@router.post("")
def create_lock(request: LockRequest, user: Dict[str, Any] = Depends(require_auth)):
    """创建锁定，若存在未过期锁则返回冲突。"""
    config = get_config()
    lock_ttl = config["locks"]["default_ttl_seconds"]

    with db_cursor() as cursor:
        cursor.execute("SELECT id FROM text_main WHERE id = %s", (request.text_id,))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文本不存在")

        cursor.execute(
            """
            SELECT id, user_id, expires_at
            FROM text_locks
            WHERE text_id = %s AND released_at IS NULL
            """,
            (request.text_id,),
        )
        active = cursor.fetchone()
        now = _utc_now()

        if active is not None:
            if active["expires_at"] > now:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="文本已被锁定")
            cursor.execute(
                "UPDATE text_locks SET released_at = %s WHERE id = %s",
                (now, active["id"]),
            )

        expires_at = now + timedelta(seconds=lock_ttl)
        cursor.execute(
            """
            INSERT INTO text_locks (text_id, user_id, locked_at, expires_at, released_at)
            VALUES (%s, %s, %s, %s, NULL)
            RETURNING id
            """,
            (request.text_id, user["user_id"], now, expires_at),
        )
        lock_id = cursor.fetchone()["id"]

    return success_response({"lock_id": lock_id, "expires_at": expires_at})


@router.delete("/{lock_id}")
def release_lock(lock_id: int, user: Dict[str, Any] = Depends(require_auth)):
    """释放锁定，仅允许锁定者操作。"""
    now = _utc_now()
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, user_id, released_at
            FROM text_locks
            WHERE id = %s
            """,
            (lock_id,),
        )
        lock = cursor.fetchone()
        if lock is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="锁定不存在")
        if lock["user_id"] != user["user_id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权释放锁定")
        if lock["released_at"] is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="锁定已释放")

        cursor.execute(
            "UPDATE text_locks SET released_at = %s WHERE id = %s",
            (now, lock_id),
        )

    return success_response({"released_at": now})
