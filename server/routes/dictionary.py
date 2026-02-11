# 词典管理路由。
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from ..config import get_config
from ..db import db_cursor
from ..response import success_response
from .deps import require_auth

router = APIRouter(prefix="/dictionary", tags=["dictionary"])


class DictionaryCreateRequest(BaseModel):
    termKey: str
    termValue: str
    category: Optional[str] = None


class DictionaryUpdateRequest(BaseModel):
    termKey: str
    termValue: str
    category: Optional[str] = None
    isActive: bool


def _apply_pagination(page: int, page_size: int) -> int:
    if page < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="page 必须 >= 1")
    if page_size < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="pageSize 必须 >= 1")
    return (page - 1) * page_size


@router.get("")
def list_dictionary(
    keyword: Optional[str] = None,
    termKey: Optional[str] = None,
    termValue: Optional[str] = None,
    category: Optional[str] = None,
    isActive: Optional[bool] = None,
    page: int = 1,
    pageSize: Optional[int] = Query(default=None, alias="pageSize"),
    _: Dict[str, Any] = Depends(require_auth),
):
    """查询词典条目，支持筛选与分页。"""
    config = get_config()
    pagination = config["pagination"]
    default_page_size = pagination["default_page_size"]
    max_page_size = pagination["max_page_size"]

    effective_page_size = pageSize if pageSize is not None else default_page_size
    if effective_page_size > max_page_size:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="pageSize 超出最大限制")

    offset = _apply_pagination(page, effective_page_size)

    conditions: List[str] = []
    params: List[Any] = []

    if keyword is not None:
        conditions.append('(\"termKey\" ILIKE %s OR \"termValue\" ILIKE %s)')
        keyword_value = f"%{keyword}%"
        params.append(keyword_value)
        params.append(keyword_value)
    if termKey is not None:
        conditions.append('"termKey" ILIKE %s')
        params.append(f"%{termKey}%")
    if termValue is not None:
        conditions.append('"termValue" ILIKE %s')
        params.append(f"%{termValue}%")
    if category is not None:
        conditions.append("category = %s")
        params.append(category)
    if isActive is not None:
        conditions.append('"isActive" = %s')
        params.append(isActive)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    with db_cursor() as cursor:
        cursor.execute(
            f"SELECT COUNT(*) AS total FROM dictionary_entries {where_clause}",
            tuple(params),
        )
        total = cursor.fetchone()["total"]

        cursor.execute(
            """
            SELECT
              id,
              "termKey" AS "termKey",
              "termValue" AS "termValue",
              category,
              "isActive" AS "isActive",
              "createdAt" AS "createdAt",
              "updatedAt" AS "updatedAt"
            FROM dictionary_entries
            """
            + f" {where_clause} ORDER BY \"updatedAt\" DESC LIMIT %s OFFSET %s",
            tuple(params + [effective_page_size, offset]),
        )
        items = cursor.fetchall()

    return success_response(
        {
            "items": items,
            "total": total,
            "page": page,
            "pageSize": effective_page_size,
        }
    )


@router.post("")
def create_dictionary(request: DictionaryCreateRequest, _: Dict[str, Any] = Depends(require_auth)):
    """新增词典条目。"""
    with db_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO dictionary_entries ("termKey", "termValue", category, "isActive", "createdAt", "updatedAt")
            VALUES (%s, %s, %s, TRUE, NOW(), NOW())
            RETURNING id
            """,
            (request.termKey, request.termValue, request.category),
        )
        entry_id = cursor.fetchone()["id"]

    return success_response({"id": entry_id})


@router.put("/{entryId}")
def update_dictionary(entryId: int, request: DictionaryUpdateRequest, _: Dict[str, Any] = Depends(require_auth)):
    """更新词典条目。"""
    with db_cursor() as cursor:
        cursor.execute("SELECT id FROM dictionary_entries WHERE id = %s", (entryId,))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="词条不存在")

        cursor.execute(
            """
            UPDATE dictionary_entries
            SET "termKey" = %s, "termValue" = %s, category = %s, "isActive" = %s, "updatedAt" = NOW()
            WHERE id = %s
            """,
            (request.termKey, request.termValue, request.category, request.isActive, entryId),
        )

    return success_response({"id": entryId})
