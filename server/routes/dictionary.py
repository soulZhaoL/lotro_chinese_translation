# 词典管理路由。
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from ..config import get_config
from ..db import db_cursor
from .deps import require_auth

router = APIRouter(prefix="/dictionary", tags=["dictionary"])


class DictionaryCreateRequest(BaseModel):
    term_key: str
    term_value: str
    category: Optional[str] = None


class DictionaryUpdateRequest(BaseModel):
    term_key: str
    term_value: str
    category: Optional[str] = None
    is_active: bool


def _apply_pagination(page: int, page_size: int) -> int:
    if page < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="page 必须 >= 1")
    if page_size < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="page_size 必须 >= 1")
    return (page - 1) * page_size


@router.get("")
def list_dictionary(
    keyword: Optional[str] = None,
    category: Optional[str] = None,
    is_active: Optional[bool] = Query(default=None, alias="is_active"),
    page: int = 1,
    page_size: Optional[int] = Query(default=None, alias="page_size"),
    _: Dict[str, Any] = Depends(require_auth),
):
    """查询词典条目，支持筛选与分页。"""
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

    if keyword is not None:
        conditions.append("(term_key ILIKE %s OR term_value ILIKE %s)")
        keyword_value = f"%{keyword}%"
        params.append(keyword_value)
        params.append(keyword_value)
    if category is not None:
        conditions.append("category = %s")
        params.append(category)
    if is_active is not None:
        conditions.append("is_active = %s")
        params.append(is_active)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    with db_cursor() as cursor:
        cursor.execute(
            f"SELECT COUNT(*) AS total FROM dictionary_entries {where_clause}",
            tuple(params),
        )
        total = cursor.fetchone()["total"]

        cursor.execute(
            """
            SELECT id, term_key, term_value, category, is_active, created_at, updated_at
            FROM dictionary_entries
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


@router.post("")
def create_dictionary(request: DictionaryCreateRequest, _: Dict[str, Any] = Depends(require_auth)):
    """新增词典条目。"""
    with db_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO dictionary_entries (term_key, term_value, category, is_active, created_at, updated_at)
            VALUES (%s, %s, %s, TRUE, NOW(), NOW())
            RETURNING id
            """,
            (request.term_key, request.term_value, request.category),
        )
        entry_id = cursor.fetchone()["id"]

    return {"id": entry_id}


@router.put("/{entry_id}")
def update_dictionary(entry_id: int, request: DictionaryUpdateRequest, _: Dict[str, Any] = Depends(require_auth)):
    """更新词典条目。"""
    with db_cursor() as cursor:
        cursor.execute("SELECT id FROM dictionary_entries WHERE id = %s", (entry_id,))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="词条不存在")

        cursor.execute(
            """
            UPDATE dictionary_entries
            SET term_key = %s, term_value = %s, category = %s, is_active = %s, updated_at = NOW()
            WHERE id = %s
            """,
            (request.term_key, request.term_value, request.category, request.is_active, entry_id),
        )

    return {"id": entry_id}
