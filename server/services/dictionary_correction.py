# 词典系统纠错服务。
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from ..db import db_cursor, get_raw_connection

SYSTEM_USERNAME = "SYSTEM"

CORRECTION_STATUS_IDLE = 0
CORRECTION_STATUS_PENDING = 1
CORRECTION_STATUS_RUNNING = 2
CORRECTION_STATUS_DONE = 3
CORRECTION_STATUS_FAILED = 4


@dataclass
class CorrectionResult:
    dictionary_id: int
    matched_text_count: int
    updated_text_count: int
    status: int
    applied_version: int
    started_at: Optional[str]
    finished_at: Optional[str]
    error: Optional[str]


@dataclass
class TextCorrectionAnalysis:
    source_match_count: int
    translated_match_count: int
    after_text: str


def normalize_variant_values(values: Any) -> List[str]:
    parsed_values = values
    if values is None:
        return []
    if isinstance(values, (bytes, bytearray)):
        parsed_values = values.decode("utf-8")
    if isinstance(parsed_values, str):
        try:
            parsed_values = json.loads(parsed_values)
        except json.JSONDecodeError as error:
            raise RuntimeError(f'dictionary variantValues JSON 解析失败: {error.msg}') from error
    if not isinstance(parsed_values, list):
        raise RuntimeError("dictionary variantValues 必须为数组")

    result: List[str] = []
    seen = set()
    for index, item in enumerate(parsed_values, start=1):
        if not isinstance(item, str):
            raise RuntimeError(f"dictionary variantValues 第 {index} 项必须为字符串")
        cleaned = item.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result


def resolve_correction_status(is_active: bool, variant_values: List[str]) -> int:
    if not is_active or not variant_values:
        return CORRECTION_STATUS_IDLE
    return CORRECTION_STATUS_PENDING


def should_requeue_correction(
    is_active: bool,
    variant_values: List[str],
    changed: bool,
    current_version: int,
    applied_version: int,
    current_status: int,
) -> Dict[str, Any]:
    if not is_active or not variant_values:
        return {
            "correctionVersion": current_version,
            "correctionStatus": CORRECTION_STATUS_IDLE,
            "appliedCorrectionVersion": current_version,
            "resetCorrectionMeta": True,
        }
    if changed:
        next_version = current_version + 1
        return {
            "correctionVersion": next_version,
            "correctionStatus": CORRECTION_STATUS_PENDING,
            "appliedCorrectionVersion": applied_version,
            "resetCorrectionMeta": True,
        }
    return {
        "correctionVersion": current_version,
        "correctionStatus": current_status,
        "appliedCorrectionVersion": applied_version,
        "resetCorrectionMeta": False,
    }


def get_system_user_id() -> int:
    with db_cursor() as cursor:
        cursor.execute('SELECT id FROM users WHERE username = %s', (SYSTEM_USERNAME,))
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("SYSTEM 用户不存在")
        return int(row["id"])


def fetch_pending_dictionary_ids(limit: int) -> List[int]:
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT id
            FROM dictionary_entries
            WHERE "correctionStatus" IN (%s, %s)
              AND "correctionVersion" > "appliedCorrectionVersion"
            ORDER BY "uptTime" ASC, id ASC
            LIMIT %s
            """,
            (CORRECTION_STATUS_PENDING, CORRECTION_STATUS_FAILED, limit),
        )
        return [int(row["id"]) for row in cursor.fetchall()]


def acquire_correction_lock(lock_name: str):
    connection = get_raw_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT GET_LOCK(%s, 0) AS acquired", (lock_name,))
            row = cursor.fetchone()
            if row and row["acquired"] == 1:
                return connection
    except Exception:
        connection.close()
        raise
    connection.close()
    return None


def release_correction_lock(lock_name: str, connection) -> None:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT RELEASE_LOCK(%s)", (lock_name,))
    finally:
        connection.close()


def _count_non_overlapping_occurrences(text: str, needle: str) -> int:
    if not text or not needle:
        return 0
    count = 0
    start = 0
    while True:
        match_index = text.find(needle, start)
        if match_index < 0:
            return count
        count += 1
        start = match_index + len(needle)


def _analyze_and_replace_variants(text: Optional[str], variants: List[str], term_value: str) -> TextCorrectionAnalysis:
    source_text = text or ""
    if not source_text:
        return TextCorrectionAnalysis(source_match_count=0, translated_match_count=0, after_text="")

    sorted_variants = sorted(variants, key=len, reverse=True)
    translated_match_count = 0
    result_parts: List[str] = []
    cursor = 0
    text_length = len(source_text)

    while cursor < text_length:
        matched_variant = None
        for variant in sorted_variants:
            if source_text.startswith(variant, cursor):
                matched_variant = variant
                break
        if matched_variant is None:
            result_parts.append(source_text[cursor])
            cursor += 1
            continue
        translated_match_count += 1
        result_parts.append(term_value)
        cursor += len(matched_variant)

    return TextCorrectionAnalysis(
        source_match_count=0,
        translated_match_count=translated_match_count,
        after_text="".join(result_parts),
    )


def _build_text_correction_analysis(source_text: Optional[str], translated_text: Optional[str], term_key: str, variants: List[str], term_value: str) -> TextCorrectionAnalysis:
    source_match_count = _count_non_overlapping_occurrences(source_text or "", term_key)
    translated_analysis = _analyze_and_replace_variants(translated_text, variants, term_value)
    return TextCorrectionAnalysis(
        source_match_count=source_match_count,
        translated_match_count=translated_analysis.translated_match_count,
        after_text=translated_analysis.after_text,
    )


def _insert_correction_log(
    cursor,
    *,
    dictionary_entry_id: int,
    correction_version: int,
    text_main_id: int,
    fid: str,
    text_id: str,
    action: str,
    reason: str,
    source_match_count: int,
    translated_match_count: int,
) -> None:
    cursor.execute(
        """
        INSERT INTO dictionary_correction_logs (
          "dictionaryEntryId",
          "correctionVersion",
          "textMainId",
          fid,
          "textId",
          action,
          reason,
          "sourceMatchCount",
          "translatedMatchCount",
          "crtTime"
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """,
        (
            dictionary_entry_id,
            correction_version,
            text_main_id,
            fid,
            text_id,
            action,
            reason,
            source_match_count,
            translated_match_count,
        ),
    )


def run_dictionary_correction(entry_id: int) -> CorrectionResult:
    system_user_id = get_system_user_id()
    started_at = datetime.now().isoformat()
    matched_text_count = 0
    updated_text_count = 0
    skipped_text_count = 0

    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT
              id,
              "termKey" AS "termKey",
              "termValue" AS "termValue",
              "variantValues" AS "variantValues",
              "isActive" AS "isActive",
              "correctionVersion" AS "correctionVersion",
              "appliedCorrectionVersion" AS "appliedCorrectionVersion"
            FROM dictionary_entries
            WHERE id = %s
            FOR UPDATE
            """,
            (entry_id,),
        )
        entry = cursor.fetchone()
        if entry is None:
            raise RuntimeError("词典条目不存在")

        variant_values = normalize_variant_values(entry["variantValues"])
        correction_version = int(entry["correctionVersion"])
        if not entry["isActive"] or not variant_values:
            cursor.execute(
                """
                UPDATE dictionary_entries
                SET
                  "correctionStatus" = %s,
                  "appliedCorrectionVersion" = "correctionVersion",
                  "correctionLastStartedAt" = NOW(),
                  "correctionLastFinishedAt" = NOW(),
                  "correctionLastError" = NULL,
                  "correctionUpdatedTextCount" = 0
                WHERE id = %s
                """,
                (CORRECTION_STATUS_IDLE, entry_id),
            )
            result = CorrectionResult(
                dictionary_id=entry_id,
                matched_text_count=0,
                updated_text_count=0,
                status=CORRECTION_STATUS_IDLE,
                applied_version=correction_version,
                started_at=started_at,
                finished_at=datetime.now().isoformat(),
                error=None,
            )
            logger.info(
                "dictionary correction skipped: entryId={} termKey={} isActive={} variantCount={} status={}",
                entry_id,
                entry["termKey"],
                bool(entry["isActive"]),
                len(variant_values),
                CORRECTION_STATUS_IDLE,
            )
            return result

        cursor.execute(
            """
            UPDATE dictionary_entries
            SET
              "correctionStatus" = %s,
              "correctionLastStartedAt" = NOW(),
              "correctionLastFinishedAt" = NULL,
              "correctionLastError" = NULL
            WHERE id = %s
            """,
            (CORRECTION_STATUS_RUNNING, entry_id),
        )
        cursor.execute(
            """
            DELETE FROM dictionary_correction_logs
            WHERE "dictionaryEntryId" = %s AND "correctionVersion" = %s
            """,
            (entry_id, correction_version),
        )

        source_pattern = f"%{entry['termKey']}%"
        translated_conditions = " OR ".join(['"translatedText" LIKE %s' for _ in variant_values])
        translated_params = [f"%{variant}%" for variant in variant_values]
        cursor.execute(
            f"""
            SELECT
              id,
              fid,
              "textId" AS "textId",
              "sourceText" AS "sourceText",
              "translatedText" AS "translatedText",
              status
            FROM text_main
            WHERE "sourceText" LIKE %s
              AND ({translated_conditions})
            FOR UPDATE
            """,
            tuple([source_pattern, *translated_params]),
        )
        rows = cursor.fetchall()

        for row in rows:
            analysis = _build_text_correction_analysis(
                row.get("sourceText"),
                row.get("translatedText"),
                entry["termKey"],
                variant_values,
                entry["termValue"],
            )
            before_text = row["translatedText"] or ""
            if analysis.source_match_count <= 0 or analysis.translated_match_count <= 0:
                skipped_text_count += 1
                _insert_correction_log(
                    cursor,
                    dictionary_entry_id=entry_id,
                    correction_version=correction_version,
                    text_main_id=int(row["id"]),
                    fid=str(row["fid"]),
                    text_id=str(row["textId"]),
                    action="skipped",
                    reason="原文或译文匹配次数为 0",
                    source_match_count=analysis.source_match_count,
                    translated_match_count=analysis.translated_match_count,
                )
                continue
            if analysis.source_match_count != analysis.translated_match_count:
                skipped_text_count += 1
                _insert_correction_log(
                    cursor,
                    dictionary_entry_id=entry_id,
                    correction_version=correction_version,
                    text_main_id=int(row["id"]),
                    fid=str(row["fid"]),
                    text_id=str(row["textId"]),
                    action="skipped",
                    reason=f"原文匹配 {analysis.source_match_count} 次，译文匹配 {analysis.translated_match_count} 次，次数不一致",
                    source_match_count=analysis.source_match_count,
                    translated_match_count=analysis.translated_match_count,
                )
                continue
            matched_text_count += 1
            after_text = analysis.after_text
            if after_text == before_text:
                skipped_text_count += 1
                _insert_correction_log(
                    cursor,
                    dictionary_entry_id=entry_id,
                    correction_version=correction_version,
                    text_main_id=int(row["id"]),
                    fid=str(row["fid"]),
                    text_id=str(row["textId"]),
                    action="skipped",
                    reason="替换后文本未变化",
                    source_match_count=analysis.source_match_count,
                    translated_match_count=analysis.translated_match_count,
                )
                continue
            cursor.execute(
                """
                UPDATE text_main
                SET "translatedText" = %s, "editCount" = "editCount" + 1, "uptTime" = NOW()
                WHERE id = %s
                """,
                (after_text, row["id"]),
            )
            cursor.execute(
                """
                INSERT INTO text_changes ("textId", "userId", "beforeText", "afterText", reason)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    row["id"],
                    system_user_id,
                    before_text,
                    after_text,
                    f"SYSTEM纠错[词典#{entry_id}][{entry['termKey']}]: {' | '.join(variant_values)} -> {entry['termValue']}",
                ),
            )
            _insert_correction_log(
                cursor,
                dictionary_entry_id=entry_id,
                correction_version=correction_version,
                text_main_id=int(row["id"]),
                fid=str(row["fid"]),
                text_id=str(row["textId"]),
                action="updated",
                reason="原文与译文匹配次数一致，已执行纠错",
                source_match_count=analysis.source_match_count,
                translated_match_count=analysis.translated_match_count,
            )
            updated_text_count += 1

        correction_last_error = None
        if skipped_text_count > 0:
            correction_last_error = (
                f"存在 {skipped_text_count} 条异常记录，请查看纠错异常记录"
            )

        cursor.execute(
            """
            UPDATE dictionary_entries
            SET
              "correctionStatus" = %s,
              "appliedCorrectionVersion" = "correctionVersion",
              "correctionLastFinishedAt" = NOW(),
              "correctionLastError" = %s,
              "correctionUpdatedTextCount" = %s
            WHERE id = %s
            """,
            (CORRECTION_STATUS_DONE, correction_last_error, updated_text_count, entry_id),
        )
        applied_version = correction_version

    finished_at = datetime.now().isoformat()
    logger.info(
        "dictionary correction complete: entryId={} matchedTextCount={} updatedTextCount={} skippedTextCount={}",
        entry_id,
        matched_text_count,
        updated_text_count,
        skipped_text_count,
    )
    return CorrectionResult(
        dictionary_id=entry_id,
        matched_text_count=matched_text_count,
        updated_text_count=updated_text_count,
        status=CORRECTION_STATUS_DONE,
        applied_version=applied_version,
        started_at=started_at,
        finished_at=finished_at,
        error=None,
    )


def mark_dictionary_correction_failed(entry_id: int, error_message: str) -> None:
    with db_cursor() as cursor:
        cursor.execute(
            """
            UPDATE dictionary_entries
            SET
              "correctionStatus" = %s,
              "correctionLastFinishedAt" = NOW(),
              "correctionLastError" = %s
            WHERE id = %s
            """,
            (CORRECTION_STATUS_FAILED, error_message[:255], entry_id),
        )
