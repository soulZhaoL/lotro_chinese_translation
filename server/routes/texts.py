# 主文本列表与详情路由。
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..config import get_config
from ..db import db_cursor
from .deps import require_auth

router = APIRouter(prefix="/texts", tags=["texts"])


def _apply_pagination(page: int, page_size: int) -> int:
    if page < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="page 必须 >= 1")
    if page_size < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="page_size 必须 >= 1")
    return (page - 1) * page_size


@router.get("")
def list_texts(
    fid: Optional[str] = None,
    part: Optional[str] = None,
    status_filter: Optional[str] = Query(default=None, alias="status"),
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: Optional[int] = Query(default=None, alias="page_size"),
    _: Dict[str, Any] = Depends(require_auth),
):
    """获取主文本列表，支持筛选与分页。"""
    config = get_config()
    pagination = config["pagination"]
    default_page_size = pagination["default_page_size"]
    max_page_size = pagination["max_page_size"]

    effective_page_size = page_size if page_size is not None else default_page_size
    if effective_page_size > max_page_size:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="page_size 超出最大限制")

    offset = _apply_pagination(page, effective_page_size)

    conditions: List[str] = []
    params: List[Any] = []

    if fid is not None:
        conditions.append("fid = %s")
        params.append(fid)
    if part is not None:
        conditions.append("part = %s")
        params.append(part)
    if status_filter is not None:
        conditions.append("status = %s")
        params.append(status_filter)
    if keyword is not None:
        conditions.append("(source_text ILIKE %s OR translated_text ILIKE %s)")
        keyword_value = f"%{keyword}%"
        params.append(keyword_value)
        params.append(keyword_value)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    with db_cursor() as cursor:
        cursor.execute(
            f"SELECT COUNT(*) AS total FROM text_main {where_clause}",
            tuple(params),
        )
        total = cursor.fetchone()["total"]

        cursor.execute(
            """
            SELECT id, fid, part, source_text, translated_text, status, edit_count, updated_at, created_at
            FROM text_main
            """
            + f" {where_clause} ORDER BY updated_at DESC LIMIT %s OFFSET %s",
            tuple(params + [effective_page_size, offset]),
        )
        items = cursor.fetchall()

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": effective_page_size,
    }


@router.get("/{text_id}")
def get_text(text_id: int, _: Dict[str, Any] = Depends(require_auth)):
    """获取主文本详情以及认领/锁定信息。"""
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, fid, part, source_text, translated_text, status, edit_count, updated_at, created_at
            FROM text_main
            WHERE id = %s
            """,
            (text_id,),
        )
        text = cursor.fetchone()
        if text is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文本不存在")

        cursor.execute(
            """
            SELECT id, user_id, claimed_at
            FROM text_claims
            WHERE text_id = %s
            ORDER BY claimed_at DESC
            """,
            (text_id,),
        )
        claims = cursor.fetchall()

        cursor.execute(
            """
            SELECT id, user_id, locked_at, expires_at, released_at
            FROM text_locks
            WHERE text_id = %s
            ORDER BY locked_at DESC
            """,
            (text_id,),
        )
        locks = cursor.fetchall()

    return {
        "text": text,
        "claims": claims,
        "locks": locks,
    }
