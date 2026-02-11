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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="pageSize 必须 >= 1")
    return (page - 1) * page_size


@router.get("")
def list_texts(
    fid: Optional[str] = None,
    status_filter: Optional[int] = Query(default=None, alias="status"),
    sourceKeyword: Optional[str] = None,
    translatedKeyword: Optional[str] = None,
    updatedFrom: Optional[str] = None,
    updatedTo: Optional[str] = None,
    claimer: Optional[str] = None,
    claimed: Optional[bool] = None,
    page: int = 1,
    pageSize: Optional[int] = Query(default=None, alias="pageSize"),
    _: Dict[str, Any] = Depends(require_auth),
):
    """获取父级主文本列表（仅 part=1），支持筛选与分页。"""
    return list_parent_texts(
        fid=fid,
        status_filter=status_filter,
        sourceKeyword=sourceKeyword,
        translatedKeyword=translatedKeyword,
        updatedFrom=updatedFrom,
        updatedTo=updatedTo,
        claimer=claimer,
        claimed=claimed,
        page=page,
        pageSize=pageSize,
        _=_,
    )


@router.get("/parents")
def list_parent_texts(
    fid: Optional[str] = None,
    status_filter: Optional[int] = Query(default=None, alias="status"),
    sourceKeyword: Optional[str] = None,
    translatedKeyword: Optional[str] = None,
    updatedFrom: Optional[str] = None,
    updatedTo: Optional[str] = None,
    claimer: Optional[str] = None,
    claimed: Optional[bool] = None,
    page: int = 1,
    pageSize: Optional[int] = Query(default=None, alias="pageSize"),
    _: Dict[str, Any] = Depends(require_auth),
):
    """获取父级主文本列表（仅 part=1），支持筛选与分页。"""
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
    if sourceKeyword is not None:
        conditions.append(
            """
            EXISTS (
                SELECT 1
                FROM text_main tmx
                WHERE tmx.fid = tm.fid
                  AND tmx."sourceText" ILIKE %s
            )
            """
        )
        params.append(f"%{sourceKeyword}%")
    if translatedKeyword is not None:
        conditions.append(
            """
            EXISTS (
                SELECT 1
                FROM text_main tmx
                WHERE tmx.fid = tm.fid
                  AND tmx."translatedText" ILIKE %s
            )
            """
        )
        params.append(f"%{translatedKeyword}%")
    if updatedFrom is not None:
        conditions.append('tm."uptTime" >= %s')
        params.append(updatedFrom)
    if updatedTo is not None:
        conditions.append('tm."uptTime" <= %s')
        params.append(updatedTo)
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
                SELECT c.id, c."userId", c."claimedAt"
                FROM text_claims c
                WHERE c."textId" = tm.id
                ORDER BY c."claimedAt" DESC
                LIMIT 1
            ) tc ON true
            LEFT JOIN users u ON u.id = tc."userId"
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
              tm."textId" AS "textId",
              tm.part,
              CASE
                WHEN length(tm."sourceText") > %s THEN substring(tm."sourceText" from 1 for %s) || '...'
                ELSE tm."sourceText"
              END AS "sourceText",
              CASE
                WHEN tm."translatedText" IS NOT NULL AND length(tm."translatedText") > %s
                  THEN substring(tm."translatedText" from 1 for %s) || '...'
                ELSE tm."translatedText"
              END AS "translatedText",
              tm.status,
              tm."editCount" AS "editCount",
              tm."uptTime" AS "uptTime",
              tm."crtTime" AS "crtTime",
              tc.id AS "claimId",
              u.username AS "claimedBy",
              tc."claimedAt" AS "claimedAt",
              CASE WHEN tc.id IS NULL THEN FALSE ELSE TRUE END AS "isClaimed"
            FROM text_main tm
            LEFT JOIN LATERAL (
                SELECT c.id, c."userId", c."claimedAt"
                FROM text_claims c
                WHERE c."textId" = tm.id
                ORDER BY c."claimedAt" DESC
                LIMIT 1
            ) tc ON true
            LEFT JOIN users u ON u.id = tc."userId"
            {where_clause}
            ORDER BY tm."uptTime" DESC
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
            "pageSize": effective_page_size,
        }
    )


@router.get("/children")
def list_child_texts(
    fid: str,
    textId: Optional[int] = Query(default=None, alias="textId"),
    sourceKeyword: Optional[str] = None,
    translatedKeyword: Optional[str] = None,
    page: int = 1,
    pageSize: Optional[int] = Query(default=None, alias="pageSize"),
    _: Dict[str, Any] = Depends(require_auth),
):
    """获取指定 fid 的子列表（默认排除 part=1），支持筛选与分页。"""
    config = get_config()
    pagination = config["pagination"]
    default_page_size = pagination["default_page_size"]
    max_page_size = pagination["max_page_size"]

    effective_page_size = pageSize if pageSize is not None else default_page_size
    if effective_page_size > max_page_size:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="pageSize 超出最大限制")

    offset = _apply_pagination(page, effective_page_size)

    params: List[Any] = [fid]
    where_clause = "WHERE tm.fid = %s AND tm.part <> 1"
    if textId is not None:
        where_clause += ' AND tm."textId" = %s'
        params.append(textId)
    if sourceKeyword is not None:
        where_clause += ' AND tm."sourceText" ILIKE %s'
        params.append(f"%{sourceKeyword}%")
    if translatedKeyword is not None:
        where_clause += ' AND tm."translatedText" ILIKE %s'
        params.append(f"%{translatedKeyword}%")

    max_text_length = config["text_list"]["max_text_length"]

    with db_cursor() as cursor:
        if textId is not None:
            cursor.execute(
                """
                SELECT COUNT(*) AS cnt
                FROM text_main
                WHERE fid = %s AND "textId" = %s
                """,
                (fid, textId),
            )
            if cursor.fetchone()["cnt"] > 1:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="textId 在该 fid 下存在重复数据")

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
              tm."textId" AS "textId",
              tm.part,
              CASE
                WHEN length(tm."sourceText") > %s THEN substring(tm."sourceText" from 1 for %s) || '...'
                ELSE tm."sourceText"
              END AS "sourceText",
              CASE
                WHEN tm."translatedText" IS NOT NULL AND length(tm."translatedText") > %s
                  THEN substring(tm."translatedText" from 1 for %s) || '...'
                ELSE tm."translatedText"
              END AS "translatedText",
              tm.status,
              tm."editCount" AS "editCount",
              tm."uptTime" AS "uptTime",
              tm."crtTime" AS "crtTime",
              tc.id AS "claimId",
              u.username AS "claimedBy",
              tc."claimedAt" AS "claimedAt",
              CASE WHEN tc.id IS NULL THEN FALSE ELSE TRUE END AS "isClaimed"
            FROM text_main tm
            LEFT JOIN LATERAL (
                SELECT c.id, c."userId", c."claimedAt"
                FROM text_claims c
                WHERE c."textId" = tm.id
                ORDER BY c."claimedAt" DESC
                LIMIT 1
            ) tc ON true
            LEFT JOIN users u ON u.id = tc."userId"
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
            "pageSize": effective_page_size,
        }
    )


@router.get("/by-textid")
def get_text_by_textid(
    fid: str,
    textId: int = Query(..., alias="textId"),
    _: Dict[str, Any] = Depends(require_auth),
):
    """根据 fid + textId 获取主文本详情。"""
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT
              id,
              fid,
              "textId" AS "textId",
              part,
              "sourceText" AS "sourceText",
              "translatedText" AS "translatedText",
              status,
              "editCount" AS "editCount",
              "uptTime" AS "uptTime",
              "crtTime" AS "crtTime"
            FROM text_main
            WHERE fid = %s AND "textId" = %s
            """,
            (fid, textId),
        )
        rows = cursor.fetchall()
        if not rows:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文本不存在")
        if len(rows) > 1:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="textId 在该 fid 下存在重复数据")
        text = rows[0]

        cursor.execute(
            """
            SELECT id, "userId" AS "userId", "claimedAt" AS "claimedAt"
            FROM text_claims
            WHERE "textId" = %s
            ORDER BY "claimedAt" DESC
            """,
            (text["id"],),
        )
        claims = cursor.fetchall()

        cursor.execute(
            """
            SELECT
              id,
              "userId" AS "userId",
              "lockedAt" AS "lockedAt",
              "expiresAt" AS "expiresAt",
              "releasedAt" AS "releasedAt"
            FROM text_locks
            WHERE "textId" = %s
            ORDER BY "lockedAt" DESC
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


@router.get("/{textId}")
def get_text(textId: int, _: Dict[str, Any] = Depends(require_auth)):
    """获取主文本详情以及认领/锁定信息。"""
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT
              id,
              fid,
              "textId" AS "textId",
              part,
              "sourceText" AS "sourceText",
              "translatedText" AS "translatedText",
              status,
              "editCount" AS "editCount",
              "uptTime" AS "uptTime",
              "crtTime" AS "crtTime"
            FROM text_main
            WHERE id = %s
            """,
            (textId,),
        )
        text = cursor.fetchone()
        if text is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文本不存在")

        cursor.execute(
            """
            SELECT id, "userId" AS "userId", "claimedAt" AS "claimedAt"
            FROM text_claims
            WHERE "textId" = %s
            ORDER BY "claimedAt" DESC
            """,
            (textId,),
        )
        claims = cursor.fetchall()

        cursor.execute(
            """
            SELECT
              id,
              "userId" AS "userId",
              "lockedAt" AS "lockedAt",
              "expiresAt" AS "expiresAt",
              "releasedAt" AS "releasedAt"
            FROM text_locks
            WHERE "textId" = %s
            ORDER BY "lockedAt" DESC
            """,
            (textId,),
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
    translatedText: str
    reason: Optional[str] = None
    isCompleted: Optional[bool] = None


@router.put("/{textId}/translate")
def update_translation(
    textId: int,
    request: TranslateRequest,
    user: Dict[str, Any] = Depends(require_auth),
):
    """保存译文并写入变更记录。"""
    with db_cursor() as cursor:
        cursor.execute(
            'SELECT "translatedText" FROM text_main WHERE id = %s',
            (textId,),
        )
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文本不存在")

        beforeText = row["translatedText"] or ""
        if request.isCompleted:
            cursor.execute(
                """
                UPDATE text_main
                SET "translatedText" = %s, status = %s, "editCount" = "editCount" + 1, "uptTime" = NOW()
                WHERE id = %s
                """,
                (request.translatedText, 3, textId),
            )
        else:
            cursor.execute(
                """
                UPDATE text_main
                SET "translatedText" = %s, status = %s, "editCount" = "editCount" + 1, "uptTime" = NOW()
                WHERE id = %s
                """,
                (request.translatedText, 2, textId),
            )
        cursor.execute(
            """
            INSERT INTO text_changes ("textId", "userId", "beforeText", "afterText", reason)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (textId, user["userId"], beforeText, request.translatedText, request.reason),
        )

    return success_response({"id": textId})
