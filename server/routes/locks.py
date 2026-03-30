# 锁定与释放相关路由。
from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel

from ..config import get_config
from ..db import db_cursor
from ..response import success_response
from .deps import require_auth

router = APIRouter(prefix="/locks", tags=["locks"])


class LockRequest(BaseModel):
    id: int


def _utc_now() -> datetime:
    return datetime.utcnow()


@router.post("")
def create_lock(request: LockRequest, user: Dict[str, Any] = Depends(require_auth)):
    """创建锁定，若存在未过期锁则返回冲突。"""
    logger.info(f"Lock create: id={request.id} userId={user['userId']}")
    config = get_config()
    lock_ttl = config["locks"]["default_ttl_seconds"]

    with db_cursor() as cursor:
        cursor.execute("SELECT id FROM text_main WHERE id = %s", (request.id,))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文本不存在")

        cursor.execute(
            """
            SELECT id, "userId", "expiresAt"
            FROM text_locks
            WHERE "textId" = %s AND "releasedAt" IS NULL
            """,
            (request.id,),
        )
        active = cursor.fetchone()
        now = _utc_now()

        if active is not None:
            if active["expiresAt"] > now:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="文本已被锁定")
            cursor.execute(
                'UPDATE text_locks SET "releasedAt" = %s WHERE id = %s',
                (now, active["id"]),
            )

        expiresAt = now + timedelta(seconds=lock_ttl)
        cursor.execute(
            """
            INSERT INTO text_locks ("textId", "userId", "lockedAt", "expiresAt", "releasedAt")
            VALUES (%s, %s, %s, %s, NULL)
            """,
            (request.id, user["userId"], now, expiresAt),
        )
        lockId = cursor.lastrowid

    logger.info(f"Lock created: lockId={lockId} id={request.id} userId={user['userId']} expiresAt={expiresAt}")
    return success_response({"lockId": lockId, "expiresAt": expiresAt})


@router.delete("/{lockId}")
def release_lock(lockId: int, user: Dict[str, Any] = Depends(require_auth)):
    """释放锁定，仅允许锁定者操作。"""
    logger.info(f"Lock release: lockId={lockId} userId={user['userId']}")
    now = _utc_now()
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, "userId", "releasedAt"
            FROM text_locks
            WHERE id = %s
            """,
            (lockId,),
        )
        lock = cursor.fetchone()
        if lock is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="锁定不存在")
        if lock["userId"] != user["userId"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权释放锁定")
        if lock["releasedAt"] is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="锁定已释放")

        cursor.execute(
            'UPDATE text_locks SET "releasedAt" = %s WHERE id = %s',
            (now, lockId),
        )

    logger.info(f"Lock released: lockId={lockId} userId={user['userId']} releasedAt={now}")
    return success_response({"releasedAt": now})
