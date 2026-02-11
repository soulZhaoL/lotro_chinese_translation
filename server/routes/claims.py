# 认领相关路由。
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..db import db_cursor
from ..response import success_response
from .deps import require_auth

router = APIRouter(prefix="/claims", tags=["claims"])


class ClaimRequest(BaseModel):
    textId: int


@router.post("")
def create_claim(request: ClaimRequest, user: Dict[str, Any] = Depends(require_auth)):
    """创建认领记录，重复认领自动忽略。"""
    with db_cursor() as cursor:
        cursor.execute("SELECT id FROM text_main WHERE id = %s", (request.textId,))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文本不存在")

        cursor.execute(
            """
            INSERT INTO text_claims ("textId", "userId")
            VALUES (%s, %s)
            ON CONFLICT ("textId", "userId") DO NOTHING
            RETURNING id
            """,
            (request.textId, user["userId"]),
        )
        row = cursor.fetchone()

        if row is None:
            cursor.execute(
                'SELECT id FROM text_claims WHERE "textId" = %s AND "userId" = %s',
                (request.textId, user["userId"]),
            )
            existing = cursor.fetchone()
            if existing is None:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="认领失败")
            claimId = existing["id"]
        else:
            claimId = row["id"]

    return success_response({"claimId": claimId})


@router.delete("/{claimId}")
def release_claim(claimId: int, user: Dict[str, Any] = Depends(require_auth)):
    """释放认领，仅允许本人释放。"""
    with db_cursor() as cursor:
        cursor.execute(
            'SELECT id, "userId" FROM text_claims WHERE id = %s',
            (claimId,),
        )
        claim = cursor.fetchone()
        if claim is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="认领不存在")
        if claim["userId"] != user["userId"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权释放认领")

        cursor.execute("DELETE FROM text_claims WHERE id = %s", (claimId,))

    return success_response({"id": claimId})
