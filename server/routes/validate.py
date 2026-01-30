# 文本校验路由。
import re
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..db import db_cursor
from .deps import require_auth

router = APIRouter(prefix="/validate", tags=["validation"])


class ValidateRequest(BaseModel):
    text_id: int
    translated_text: str


PLACEHOLDER_PATTERN = re.compile(r"\{[^}]+\}")
PERCENT_PATTERN = re.compile(r"%[sd]")


def _extract_placeholders(text: str) -> List[str]:
    return PLACEHOLDER_PATTERN.findall(text)


def _extract_percent_tokens(text: str) -> List[str]:
    return PERCENT_PATTERN.findall(text)


@router.post("")
def validate_text(request: ValidateRequest, _: Dict[str, Any] = Depends(require_auth)):
    """校验译文格式并返回错误列表。"""
    with db_cursor() as cursor:
        cursor.execute("SELECT source_text FROM text_main WHERE id = %s", (request.text_id,))
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文本不存在")
        source_text = row["source_text"]

    errors: List[str] = []

    if not request.translated_text.strip():
        errors.append("译文不能为空")

    source_placeholders = _extract_placeholders(source_text)
    translated_placeholders = _extract_placeholders(request.translated_text)
    if len(source_placeholders) != len(translated_placeholders):
        errors.append("花括号占位符数量不一致")

    source_percents = _extract_percent_tokens(source_text)
    translated_percents = _extract_percent_tokens(request.translated_text)
    if len(source_percents) != len(translated_percents):
        errors.append("百分号占位符数量不一致")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }
