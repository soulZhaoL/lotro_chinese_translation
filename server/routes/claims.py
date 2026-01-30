# 认领相关路由。
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..db import db_cursor
from .deps import require_auth

router = APIRouter(prefix="/claims", tags=["claims"])


class ClaimRequest(BaseModel):
    text_id: int


@router.post("")
def create_claim(request: ClaimRequest, user: Dict[str, Any] = Depends(require_auth)):
    """创建认领记录，重复认领自动忽略。"""
    with db_cursor() as cursor:
        cursor.execute("SELECT id FROM text_main WHERE id = %s", (request.text_id,))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文本不存在")

        cursor.execute(
            """
            INSERT INTO text_claims (text_id, user_id)
            VALUES (%s, %s)
            ON CONFLICT (text_id, user_id) DO NOTHING
            RETURNING id
            """,
            (request.text_id, user["user_id"]),
        )
        row = cursor.fetchone()

        if row is None:
            cursor.execute(
                "SELECT id FROM text_claims WHERE text_id = %s AND user_id = %s",
                (request.text_id, user["user_id"]),
            )
            existing = cursor.fetchone()
            if existing is None:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="认领失败")
            claim_id = existing["id"]
        else:
            claim_id = row["id"]

    return {"claim_id": claim_id}
