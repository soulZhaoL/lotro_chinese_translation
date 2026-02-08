# 主文本列表与详情路由。
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from ..config import get_config
from ..db import db_cursor
from ..response import success_response
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
    status_filter: Optional[int] = Query(default=None, alias="status"),
    source_keyword: Optional[str] = None,
    translated_keyword: Optional[str] = None,
    updated_from: Optional[str] = None,
    updated_to: Optional[str] = None,
    claimer: Optional[str] = None,
    claimed: Optional[bool] = None,
    page: int = 1,
    page_size: Optional[int] = Query(default=None, alias="page_size"),
    _: Dict[str, Any] = Depends(require_auth),
):
    """获取父级主文本列表（仅 part=1），支持筛选与分页。"""
    return list_parent_texts(
        fid=fid,
        status_filter=status_filter,
        source_keyword=source_keyword,
        translated_keyword=translated_keyword,
        updated_from=updated_from,
        updated_to=updated_to,
        claimer=claimer,
        claimed=claimed,
        page=page,
        page_size=page_size,
        _=_,
    )


@router.get("/parents")
def list_parent_texts(
    fid: Optional[str] = None,
    status_filter: Optional[int] = Query(default=None, alias="status"),
    source_keyword: Optional[str] = None,
    translated_keyword: Optional[str] = None,
    updated_from: Optional[str] = None,
    updated_to: Optional[str] = None,
    claimer: Optional[str] = None,
    claimed: Optional[bool] = None,
    page: int = 1,
    page_size: Optional[int] = Query(default=None, alias="page_size"),
    _: Dict[str, Any] = Depends(require_auth),
):
    """获取父级主文本列表（仅 part=1），支持筛选与分页。"""
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
        conditions.append("tm.fid = %s")
        params.append(fid)
    conditions.append("tm.part = %s")
    params.append(1)
    if status_filter is not None:
        if status_filter not in (1, 2, 3):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="status 必须为 1/2/3")
        conditions.append("tm.status = %s")
        params.append(status_filter)
    if source_keyword is not None:
        conditions.append(
            """
            EXISTS (
                SELECT 1
                FROM text_main tmx
                WHERE tmx.fid = tm.fid
                  AND tmx.source_text ILIKE %s
            )
            """
        )
        params.append(f"%{source_keyword}%")
    if translated_keyword is not None:
        conditions.append(
            """
            EXISTS (
                SELECT 1
                FROM text_main tmx
                WHERE tmx.fid = tm.fid
                  AND tmx.translated_text ILIKE %s
            )
            """
        )
        params.append(f"%{translated_keyword}%")
    if updated_from is not None:
        conditions.append("tm.updated_at >= %s")
        params.append(updated_from)
    if updated_to is not None:
        conditions.append("tm.updated_at <= %s")
        params.append(updated_to)
    if claimer is not None:
        conditions.append("u.username ILIKE %s")
        params.append(f"%{claimer}%")
    if claimed is True:
        conditions.append("tc.id IS NOT NULL")
    if claimed is False:
        conditions.append("tc.id IS NULL")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    max_text_length = config["text_list"]["max_text_length"]

    with db_cursor() as cursor:
        cursor.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM text_main tm
            LEFT JOIN LATERAL (
                SELECT c.id, c.user_id, c.claimed_at
                FROM text_claims c
                WHERE c.text_id = tm.id
                ORDER BY c.claimed_at DESC
                LIMIT 1
            ) tc ON true
            LEFT JOIN users u ON u.id = tc.user_id
            {where_clause}
            """,
            tuple(params),
        )
        total = cursor.fetchone()["total"]

        cursor.execute(
            f"""
            SELECT
              tm.id,
              tm.fid,
              tm.text_id,
              tm.part,
              CASE
                WHEN length(tm.source_text) > %s THEN substring(tm.source_text from 1 for %s) || '...'
                ELSE tm.source_text
              END AS source_text,
              CASE
                WHEN tm.translated_text IS NOT NULL AND length(tm.translated_text) > %s
                  THEN substring(tm.translated_text from 1 for %s) || '...'
                ELSE tm.translated_text
              END AS translated_text,
              tm.status,
              tm.edit_count,
              tm.updated_at,
              tm.created_at,
              tc.id AS claim_id,
              u.username AS claimed_by,
              tc.claimed_at AS claimed_at,
              CASE WHEN tc.id IS NULL THEN FALSE ELSE TRUE END AS is_claimed
            FROM text_main tm
            LEFT JOIN LATERAL (
                SELECT c.id, c.user_id, c.claimed_at
                FROM text_claims c
                WHERE c.text_id = tm.id
                ORDER BY c.claimed_at DESC
                LIMIT 1
            ) tc ON true
            LEFT JOIN users u ON u.id = tc.user_id
            {where_clause}
            ORDER BY tm.updated_at DESC
            LIMIT %s OFFSET %s
            """,
            tuple([max_text_length, max_text_length, max_text_length, max_text_length] + params + [effective_page_size, offset]),
        )
        items = cursor.fetchall()

    return success_response(
        {
            "items": items,
            "total": total,
            "page": page,
            "page_size": effective_page_size,
        }
    )


@router.get("/children")
def list_child_texts(
    fid: str,
    text_id: Optional[int] = Query(default=None, alias="text_id"),
    source_keyword: Optional[str] = None,
    translated_keyword: Optional[str] = None,
    page: int = 1,
    page_size: Optional[int] = Query(default=None, alias="page_size"),
    _: Dict[str, Any] = Depends(require_auth),
):
    """获取指定 fid 的子列表（默认排除 part=1），支持筛选与分页。"""
    config = get_config()
    pagination = config["pagination"]
    default_page_size = pagination["default_page_size"]
    max_page_size = pagination["max_page_size"]

    effective_page_size = page_size if page_size is not None else default_page_size
    if effective_page_size > max_page_size:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="page_size 超出最大限制")

    offset = _apply_pagination(page, effective_page_size)

    params: List[Any] = [fid]
    where_clause = "WHERE tm.fid = %s AND tm.part <> 1"
    if text_id is not None:
        where_clause += " AND tm.text_id = %s"
        params.append(text_id)
    if source_keyword is not None:
        where_clause += " AND tm.source_text ILIKE %s"
        params.append(f"%{source_keyword}%")
    if translated_keyword is not None:
        where_clause += " AND tm.translated_text ILIKE %s"
        params.append(f"%{translated_keyword}%")

    max_text_length = config["text_list"]["max_text_length"]

    with db_cursor() as cursor:
        if text_id is not None:
            cursor.execute(
                """
                SELECT COUNT(*) AS cnt
                FROM text_main
                WHERE fid = %s AND text_id = %s
                """,
                (fid, text_id),
            )
            if cursor.fetchone()["cnt"] > 1:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="text_id 在该 fid 下存在重复数据")

        cursor.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM text_main tm
            {where_clause}
            """,
            tuple(params),
        )
        total = cursor.fetchone()["total"]

        cursor.execute(
            f"""
            SELECT
              tm.id,
              tm.fid,
              tm.text_id,
              tm.part,
              CASE
                WHEN length(tm.source_text) > %s THEN substring(tm.source_text from 1 for %s) || '...'
                ELSE tm.source_text
              END AS source_text,
              CASE
                WHEN tm.translated_text IS NOT NULL AND length(tm.translated_text) > %s
                  THEN substring(tm.translated_text from 1 for %s) || '...'
                ELSE tm.translated_text
              END AS translated_text,
              tm.status,
              tm.edit_count,
              tm.updated_at,
              tm.created_at,
              tc.id AS claim_id,
              u.username AS claimed_by,
              tc.claimed_at AS claimed_at,
              CASE WHEN tc.id IS NULL THEN FALSE ELSE TRUE END AS is_claimed
            FROM text_main tm
            LEFT JOIN LATERAL (
                SELECT c.id, c.user_id, c.claimed_at
                FROM text_claims c
                WHERE c.text_id = tm.id
                ORDER BY c.claimed_at DESC
                LIMIT 1
            ) tc ON true
            LEFT JOIN users u ON u.id = tc.user_id
            {where_clause}
            ORDER BY tm.part ASC
            LIMIT %s OFFSET %s
            """,
            tuple([max_text_length, max_text_length, max_text_length, max_text_length] + params + [effective_page_size, offset]),
        )
        items = cursor.fetchall()

    return success_response(
        {
            "items": items,
            "total": total,
            "page": page,
            "page_size": effective_page_size,
        }
    )


@router.get("/by-textid")
def get_text_by_textid(
    fid: str,
    text_id: int = Query(..., alias="text_id"),
    _: Dict[str, Any] = Depends(require_auth),
):
    """根据 fid + textId 获取主文本详情。"""
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, fid, text_id, part, source_text, translated_text, status, edit_count, updated_at, created_at
            FROM text_main
            WHERE fid = %s AND text_id = %s
            """,
            (fid, text_id),
        )
        rows = cursor.fetchall()
        if not rows:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文本不存在")
        if len(rows) > 1:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="text_id 在该 fid 下存在重复数据")
        text = rows[0]

        cursor.execute(
            """
            SELECT id, user_id, claimed_at
            FROM text_claims
            WHERE text_id = %s
            ORDER BY claimed_at DESC
            """,
            (text["id"],),
        )
        claims = cursor.fetchall()

        cursor.execute(
            """
            SELECT id, user_id, locked_at, expires_at, released_at
            FROM text_locks
            WHERE text_id = %s
            ORDER BY locked_at DESC
            """,
            (text["id"],),
        )
        locks = cursor.fetchall()

    return success_response(
        {
            "text": text,
            "claims": claims,
            "locks": locks,
        }
    )


@router.get("/{text_id}")
def get_text(text_id: int, _: Dict[str, Any] = Depends(require_auth)):
    """获取主文本详情以及认领/锁定信息。"""
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, fid, text_id, part, source_text, translated_text, status, edit_count, updated_at, created_at
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

    return success_response(
        {
            "text": text,
            "claims": claims,
            "locks": locks,
        }
    )


class TranslateRequest(BaseModel):
    translated_text: str
    reason: Optional[str] = None
    is_completed: Optional[bool] = None


@router.put("/{text_id}/translate")
def update_translation(
    text_id: int,
    request: TranslateRequest,
    user: Dict[str, Any] = Depends(require_auth),
):
    """保存译文并写入变更记录。"""
    with db_cursor() as cursor:
        cursor.execute(
            "SELECT translated_text FROM text_main WHERE id = %s",
            (text_id,),
        )
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文本不存在")

        before_text = row["translated_text"] or ""
        if request.is_completed:
            cursor.execute(
                """
                UPDATE text_main
                SET translated_text = %s, status = %s, edit_count = edit_count + 1, updated_at = NOW()
                WHERE id = %s
                """,
                (request.translated_text, 3, text_id),
            )
        else:
            cursor.execute(
                """
                UPDATE text_main
                SET translated_text = %s, status = %s, edit_count = edit_count + 1, updated_at = NOW()
                WHERE id = %s
                """,
                (request.translated_text, 2, text_id),
            )
        cursor.execute(
            """
            INSERT INTO text_changes (text_id, user_id, before_text, after_text, reason)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (text_id, user["user_id"], before_text, request.translated_text, request.reason),
        )

    return success_response({"id": text_id})
