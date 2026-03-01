# 主文本列表与详情路由。
import os
from datetime import datetime
from io import BytesIO
from tempfile import NamedTemporaryFile
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, StreamingResponse
from openpyxl import Workbook, load_workbook
from pydantic import BaseModel
from starlette.background import BackgroundTask

from ..config import get_config
from ..db import db_cursor, db_stream_cursor
from ..response import success_response
from .deps import require_auth

router = APIRouter(prefix="/texts", tags=["texts"])


TEXT_TEMPLATE_HEADERS: Tuple[str, ...] = ("编号", "FID", "TextId", "Part", "原文", "译文", "状态")
STATUS_LABEL_TO_VALUE: Dict[str, int] = {"新增": 1, "修改": 2, "已完成": 3}
STATUS_VALUE_SET = {1, 2, 3}


def _apply_pagination(page: int, page_size: int) -> int:
    if page < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="page 必须 >= 1")
    if page_size < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="pageSize 必须 >= 1")
    return (page - 1) * page_size


def _is_empty_cell(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def _parse_required_int(value: Any, field_name: str, row_number: int) -> int:
    if _is_empty_cell(value):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"第 {row_number} 行字段 {field_name} 不能为空")
    if isinstance(value, bool):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"第 {row_number} 行字段 {field_name} 类型错误，必须为整数",
        )
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"第 {row_number} 行字段 {field_name} 类型错误，必须为整数",
    )


def _parse_status(value: Any, row_number: int) -> int:
    if _is_empty_cell(value):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"第 {row_number} 行字段 状态 不能为空")
    if isinstance(value, str):
        stripped = value.strip()
        if stripped in STATUS_LABEL_TO_VALUE:
            return STATUS_LABEL_TO_VALUE[stripped]
        if stripped.isdigit():
            status_value = int(stripped)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"第 {row_number} 行字段 状态 非法，必须为 1/2/3 或 新增/修改/已完成",
            )
    else:
        status_value = _parse_required_int(value, "状态", row_number)

    if status_value not in STATUS_VALUE_SET:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"第 {row_number} 行字段 状态 非法，必须为 1/2/3 或 新增/修改/已完成",
        )
    return status_value


def _parse_required_str(value: Any, field_name: str, row_number: int) -> str:
    if _is_empty_cell(value):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"第 {row_number} 行字段 {field_name} 不能为空")
    return str(value)


def _normalize_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _validate_template_header(header_values: List[Any]) -> None:
    if len(header_values) < len(TEXT_TEMPLATE_HEADERS):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="上传模板缺少必要列")

    expected = list(TEXT_TEMPLATE_HEADERS)
    actual = ["" if value is None else str(value).strip() for value in header_values[: len(TEXT_TEMPLATE_HEADERS)]]
    if actual != expected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"上传模板表头不匹配，必须为: {'/'.join(TEXT_TEMPLATE_HEADERS)}",
        )

    extra_values = header_values[len(TEXT_TEMPLATE_HEADERS) :]
    for column_index, value in enumerate(extra_values, start=len(TEXT_TEMPLATE_HEADERS) + 1):
        if not _is_empty_cell(value):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"上传模板存在多余表头列: 第 {column_index} 列",
            )


def _load_upload_sheet(file_bytes: bytes):
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="上传文件为空")
    try:
        workbook = load_workbook(filename=BytesIO(file_bytes), read_only=True, data_only=True)
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"上传文件解析失败: {error}") from error
    if not workbook.worksheets:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="上传文件缺少工作表")
    return workbook.worksheets[0]


def _cleanup_temp_file(path: str) -> None:
    try:
        os.remove(path)
    except FileNotFoundError:
        return


def _build_download_conditions(
    fid: Optional[str],
    status_filter: Optional[int],
    sourceKeyword: Optional[str],
    translatedKeyword: Optional[str],
    updatedFrom: Optional[str],
    updatedTo: Optional[str],
    claimer: Optional[str],
    claimed: Optional[bool],
) -> Tuple[List[str], List[Any]]:
    conditions: List[str] = []
    params: List[Any] = []

    if fid is not None:
        conditions.append("tm.fid = %s")
        params.append(fid)
    if status_filter is not None:
        if status_filter not in (1, 2, 3):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="status 必须为 1/2/3")
        conditions.append("tm.status = %s")
        params.append(status_filter)
    if sourceKeyword is not None:
        conditions.append('tm."sourceText" LIKE %s')
        params.append(f"%{sourceKeyword}%")
    if translatedKeyword is not None:
        conditions.append('tm."translatedText" LIKE %s')
        params.append(f"%{translatedKeyword}%")
    if updatedFrom is not None:
        conditions.append('tm."uptTime" >= %s')
        params.append(updatedFrom)
    if updatedTo is not None:
        conditions.append('tm."uptTime" <= %s')
        params.append(updatedTo)
    if claimer is not None:
        conditions.append(
            """
            (
              SELECT u.username
              FROM text_claims c
              JOIN users u ON u.id = c."userId"
              WHERE c."textId" = tm.id
              ORDER BY c."claimedAt" DESC, c.id DESC
              LIMIT 1
            ) LIKE %s
            """
        )
        params.append(f"%{claimer}%")
    if claimed is True:
        conditions.append('EXISTS (SELECT 1 FROM text_claims c WHERE c."textId" = tm.id)')
    if claimed is False:
        conditions.append('NOT EXISTS (SELECT 1 FROM text_claims c WHERE c."textId" = tm.id)')

    return conditions, params


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
    """获取平铺主文本列表（全量 part），支持筛选与分页。"""
    config = get_config()
    pagination = config["pagination"]
    default_page_size = pagination["default_page_size"]
    max_page_size = pagination["max_page_size"]

    effective_page_size = pageSize if pageSize is not None else default_page_size
    if effective_page_size > max_page_size:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="pageSize 超出最大限制")

    offset = _apply_pagination(page, effective_page_size)
    conditions, params = _build_download_conditions(
        fid=fid,
        status_filter=status_filter,
        sourceKeyword=sourceKeyword,
        translatedKeyword=translatedKeyword,
        updatedFrom=updatedFrom,
        updatedTo=updatedTo,
        claimer=claimer,
        claimed=claimed,
    )
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    max_text_length = config["text_list"]["max_text_length"]

    with db_cursor() as cursor:
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
                WHEN length(tm."sourceText") > %s THEN CONCAT(SUBSTRING(tm."sourceText", 1, %s), '...')
                ELSE tm."sourceText"
              END AS "sourceText",
              CASE
                WHEN tm."translatedText" IS NOT NULL AND length(tm."translatedText") > %s
                  THEN CONCAT(SUBSTRING(tm."translatedText", 1, %s), '...')
                ELSE tm."translatedText"
              END AS "translatedText",
              tm.status,
              tm."editCount" AS "editCount",
              tm."uptTime" AS "uptTime",
              tm."crtTime" AS "crtTime",
              (
                SELECT c.id
                FROM text_claims c
                WHERE c."textId" = tm.id
                ORDER BY c."claimedAt" DESC, c.id DESC
                LIMIT 1
              ) AS "claimId",
              (
                SELECT u.username
                FROM text_claims c
                JOIN users u ON u.id = c."userId"
                WHERE c."textId" = tm.id
                ORDER BY c."claimedAt" DESC, c.id DESC
                LIMIT 1
              ) AS "claimedBy",
              (
                SELECT c."claimedAt"
                FROM text_claims c
                WHERE c."textId" = tm.id
                ORDER BY c."claimedAt" DESC, c.id DESC
                LIMIT 1
              ) AS "claimedAt",
              EXISTS (
                SELECT 1
                FROM text_claims c
                WHERE c."textId" = tm.id
              ) AS "isClaimed"
            FROM text_main tm
            {where_clause}
            ORDER BY tm."uptTime" DESC, tm.id DESC
            LIMIT %s OFFSET %s
            """,
            tuple([max_text_length, max_text_length, max_text_length, max_text_length] + params + [effective_page_size, offset]),
        )
        items = cursor.fetchall()
        for item in items:
            item["isClaimed"] = bool(item["isClaimed"])

    return success_response(
        {
            "items": items,
            "total": total,
            "page": page,
            "pageSize": effective_page_size,
        }
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
                  AND tmx."sourceText" LIKE %s
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
                  AND tmx."translatedText" LIKE %s
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
        conditions.append(
            """
            (
              SELECT u.username
              FROM text_claims c
              JOIN users u ON u.id = c."userId"
              WHERE c."textId" = tm.id
              ORDER BY c."claimedAt" DESC, c.id DESC
              LIMIT 1
            ) LIKE %s
            """
        )
        params.append(f"%{claimer}%")
    if claimed is True:
        conditions.append('EXISTS (SELECT 1 FROM text_claims c WHERE c."textId" = tm.id)')
    if claimed is False:
        conditions.append('NOT EXISTS (SELECT 1 FROM text_claims c WHERE c."textId" = tm.id)')

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    max_text_length = config["text_list"]["max_text_length"]

    with db_cursor() as cursor:
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
                WHEN length(tm."sourceText") > %s THEN CONCAT(SUBSTRING(tm."sourceText", 1, %s), '...')
                ELSE tm."sourceText"
              END AS "sourceText",
              CASE
                WHEN tm."translatedText" IS NOT NULL AND length(tm."translatedText") > %s
                  THEN CONCAT(SUBSTRING(tm."translatedText", 1, %s), '...')
                ELSE tm."translatedText"
              END AS "translatedText",
              tm.status,
              tm."editCount" AS "editCount",
              tm."uptTime" AS "uptTime",
              tm."crtTime" AS "crtTime",
              (
                SELECT c.id
                FROM text_claims c
                WHERE c."textId" = tm.id
                ORDER BY c."claimedAt" DESC, c.id DESC
                LIMIT 1
              ) AS "claimId",
              (
                SELECT u.username
                FROM text_claims c
                JOIN users u ON u.id = c."userId"
                WHERE c."textId" = tm.id
                ORDER BY c."claimedAt" DESC, c.id DESC
                LIMIT 1
              ) AS "claimedBy",
              (
                SELECT c."claimedAt"
                FROM text_claims c
                WHERE c."textId" = tm.id
                ORDER BY c."claimedAt" DESC, c.id DESC
                LIMIT 1
              ) AS "claimedAt",
              EXISTS (
                SELECT 1
                FROM text_claims c
                WHERE c."textId" = tm.id
              ) AS "isClaimed"
            FROM text_main tm
            {where_clause}
            ORDER BY tm."uptTime" DESC
            LIMIT %s OFFSET %s
            """,
            tuple([max_text_length, max_text_length, max_text_length, max_text_length] + params + [effective_page_size, offset]),
        )
        items = cursor.fetchall()
        for item in items:
            item["isClaimed"] = bool(item["isClaimed"])

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
        where_clause += ' AND tm."sourceText" LIKE %s'
        params.append(f"%{sourceKeyword}%")
    if translatedKeyword is not None:
        where_clause += ' AND tm."translatedText" LIKE %s'
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
                WHEN length(tm."sourceText") > %s THEN CONCAT(SUBSTRING(tm."sourceText", 1, %s), '...')
                ELSE tm."sourceText"
              END AS "sourceText",
              CASE
                WHEN tm."translatedText" IS NOT NULL AND length(tm."translatedText") > %s
                  THEN CONCAT(SUBSTRING(tm."translatedText", 1, %s), '...')
                ELSE tm."translatedText"
              END AS "translatedText",
              tm.status,
              tm."editCount" AS "editCount",
              tm."uptTime" AS "uptTime",
              tm."crtTime" AS "crtTime",
              (
                SELECT c.id
                FROM text_claims c
                WHERE c."textId" = tm.id
                ORDER BY c."claimedAt" DESC, c.id DESC
                LIMIT 1
              ) AS "claimId",
              (
                SELECT u.username
                FROM text_claims c
                JOIN users u ON u.id = c."userId"
                WHERE c."textId" = tm.id
                ORDER BY c."claimedAt" DESC, c.id DESC
                LIMIT 1
              ) AS "claimedBy",
              (
                SELECT c."claimedAt"
                FROM text_claims c
                WHERE c."textId" = tm.id
                ORDER BY c."claimedAt" DESC, c.id DESC
                LIMIT 1
              ) AS "claimedAt",
              EXISTS (
                SELECT 1
                FROM text_claims c
                WHERE c."textId" = tm.id
              ) AS "isClaimed"
            FROM text_main tm
            {where_clause}
            ORDER BY tm.part ASC
            LIMIT %s OFFSET %s
            """,
            tuple([max_text_length, max_text_length, max_text_length, max_text_length] + params + [effective_page_size, offset]),
        )
        items = cursor.fetchall()
        for item in items:
            item["isClaimed"] = bool(item["isClaimed"])

    return success_response(
        {
            "items": items,
            "total": total,
            "page": page,
            "pageSize": effective_page_size,
        }
    )


@router.get("/template")
def download_text_template(_: Dict[str, Any] = Depends(require_auth)):
    """下载上传模板（仅表头）。"""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "texts"
    sheet.append(list(TEXT_TEMPLATE_HEADERS))

    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="text_template.xlsx"'},
    )


@router.get("/download")
def download_texts(
    fid: Optional[str] = None,
    status_filter: Optional[int] = Query(default=None, alias="status"),
    sourceKeyword: Optional[str] = None,
    translatedKeyword: Optional[str] = None,
    updatedFrom: Optional[str] = None,
    updatedTo: Optional[str] = None,
    claimer: Optional[str] = None,
    claimed: Optional[bool] = None,
    _: Dict[str, Any] = Depends(require_auth),
):
    """根据筛选条件导出文本数据（流式 + 低内存）。"""
    config = get_config()
    text_import_export = config["text_import_export"]
    max_download_rows = text_import_export["max_download_rows"]
    download_fetch_batch_size = text_import_export["download_fetch_batch_size"]
    download_temp_dir = text_import_export["download_temp_dir"]

    if not os.path.isdir(download_temp_dir):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="导出临时目录不存在")

    conditions, params = _build_download_conditions(
        fid=fid,
        status_filter=status_filter,
        sourceKeyword=sourceKeyword,
        translatedKeyword=translatedKeyword,
        updatedFrom=updatedFrom,
        updatedTo=updatedTo,
        claimer=claimer,
        claimed=claimed,
    )
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    workbook = Workbook(write_only=True)
    sheet = workbook.create_sheet(title="texts")
    sheet.append(list(TEXT_TEMPLATE_HEADERS))

    export_count = 0
    tmp_path: Optional[str] = None
    try:
        with db_stream_cursor() as cursor:
            cursor.execute(
                f"""
                SELECT
                  tm.id,
                  tm.fid,
                  tm."textId" AS "textId",
                  tm.part,
                  tm."sourceText" AS "sourceText",
                  tm."translatedText" AS "translatedText",
                  tm.status
                FROM text_main tm
                {where_clause}
                ORDER BY tm.fid ASC, tm."textId" ASC, tm.part ASC
                """,
                tuple(params),
            )
            while True:
                rows = cursor.fetchmany(download_fetch_batch_size)
                if not rows:
                    break
                for row in rows:
                    export_count += 1
                    if export_count > max_download_rows:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"导出数据量超过限制（{max_download_rows}），请缩小筛选范围后重试",
                        )
                    sheet.append(
                        [
                            row["id"],
                            row["fid"],
                            row["textId"],
                            row["part"],
                            row["sourceText"],
                            row["translatedText"],
                            row["status"],
                        ]
                    )

        if export_count == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前筛选条件无可导出数据")

        tmp_file = NamedTemporaryFile(
            prefix="tmp_text_export_",
            suffix=".xlsx",
            dir=download_temp_dir,
            delete=False,
        )
        tmp_path = tmp_file.name
        tmp_file.close()
        workbook.save(tmp_path)
    except Exception:
        workbook.close()
        if tmp_path is not None:
            _cleanup_temp_file(tmp_path)
        raise
    workbook.close()

    export_name = f"text_export_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    return FileResponse(
        path=tmp_path,
        filename=export_name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        background=BackgroundTask(_cleanup_temp_file, tmp_path),
    )


@router.post("/upload")
async def upload_text_template(
    request: Request,
    fileName: str = Query(..., alias="fileName"),
    reason: Optional[str] = Query(default=None, alias="reason"),
    user: Dict[str, Any] = Depends(require_auth),
):
    """按模板上传翻译结果并覆盖译文与状态。"""
    if not fileName:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="上传文件缺少文件名")
    if not fileName.lower().endswith(".xlsx"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="上传文件必须为 .xlsx 格式")

    config = get_config()
    text_import_export = config["text_import_export"]
    max_upload_rows = text_import_export["max_upload_rows"]

    file_bytes = await request.body()
    sheet = _load_upload_sheet(file_bytes)

    header_rows = list(sheet.iter_rows(min_row=1, max_row=1))
    if not header_rows:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="上传文件为空")
    header_values = [cell.value for cell in header_rows[0]]
    _validate_template_header(header_values)

    parsed_rows: List[Dict[str, Any]] = []
    for row_index, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
        cells = list(row[: len(TEXT_TEMPLATE_HEADERS)])
        if len(cells) < len(TEXT_TEMPLATE_HEADERS):
            cells.extend([None] * (len(TEXT_TEMPLATE_HEADERS) - len(cells)))
        if all(_is_empty_cell(item) for item in cells):
            continue

        extra_cells = list(row[len(TEXT_TEMPLATE_HEADERS) :])
        if any(not _is_empty_cell(item) for item in extra_cells):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"第 {row_index} 行存在模板外数据，请删除多余列",
            )

        row_id = _parse_required_int(cells[0], "编号", row_index)
        text_id = _parse_required_int(cells[2], "TextId", row_index)
        part = _parse_required_int(cells[3], "Part", row_index)
        if row_id <= 0 or text_id <= 0 or part <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"第 {row_index} 行编号/TextId/Part 必须 > 0")

        parsed_rows.append(
            {
                "rowNumber": row_index,
                "id": row_id,
                "fid": _parse_required_str(cells[1], "FID", row_index),
                "textId": text_id,
                "part": part,
                "translatedText": _normalize_text(cells[5]),
                "status": _parse_status(cells[6], row_index),
            }
        )

    if not parsed_rows:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="上传文件没有可处理的数据行")

    if len(parsed_rows) > max_upload_rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"上传行数超限，最大允许 {max_upload_rows} 行",
        )

    ids = [item["id"] for item in parsed_rows]
    if len(set(ids)) != len(ids):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="上传文件存在重复编号")

    placeholders = ",".join(["%s"] * len(ids))
    with db_cursor() as cursor:
        cursor.execute(
            f"""
            SELECT id, fid, "textId" AS "textId", part, "translatedText" AS "translatedText"
            FROM text_main
            WHERE id IN ({placeholders})
            """,
            tuple(ids),
        )
        db_rows = cursor.fetchall()
        db_map = {item["id"]: item for item in db_rows}

        for item in parsed_rows:
            db_item = db_map.get(item["id"])
            if db_item is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"第 {item['rowNumber']} 行编号不存在: {item['id']}",
                )
            if db_item["fid"] != item["fid"] or db_item["textId"] != item["textId"] or db_item["part"] != item["part"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"第 {item['rowNumber']} 行校验失败: 编号/FID/TextId/Part 与数据库不匹配",
                )

        for item in parsed_rows:
            db_item = db_map[item["id"]]
            before_text = db_item["translatedText"] or ""
            cursor.execute(
                """
                UPDATE text_main
                SET "translatedText" = %s, status = %s, "editCount" = "editCount" + 1, "uptTime" = NOW()
                WHERE id = %s
                """,
                (item["translatedText"], item["status"], item["id"]),
            )
            cursor.execute(
                """
                INSERT INTO text_changes ("textId", "userId", "beforeText", "afterText", reason)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (item["id"], user["userId"], before_text, item["translatedText"] or "", reason),
            )

    return success_response({"updatedCount": len(parsed_rows)})


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
