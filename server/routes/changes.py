# 变更历史查询路由。
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..db import db_cursor
from ..response import success_response
from .deps import require_auth

router = APIRouter(prefix="/changes", tags=["changes"])


@router.get("")
def list_changes(textId: int = Query(...), _: Dict[str, Any] = Depends(require_auth)):
    """查询指定文本的变更历史。"""
    with db_cursor() as cursor:
        cursor.execute("SELECT id FROM text_main WHERE id = %s", (textId,))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文本不存在")

        cursor.execute(
            """
            SELECT
              id,
              "textId" AS "textId",
              "userId" AS "userId",
              "beforeText" AS "beforeText",
              "afterText" AS "afterText",
              reason,
              "changedAt" AS "changedAt"
            FROM text_changes
            WHERE "textId" = %s
            ORDER BY "changedAt" DESC
            """,
            (textId,),
        )
        items = cursor.fetchall()

    return success_response({"items": items})
