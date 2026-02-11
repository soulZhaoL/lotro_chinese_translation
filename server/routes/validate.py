# 文本校验路由。
import re
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..db import db_cursor
from ..response import success_response
from .deps import require_auth

router = APIRouter(prefix="/validate", tags=["validation"])


class ValidateRequest(BaseModel):
    textId: int
    translatedText: str


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
        cursor.execute('SELECT "sourceText" FROM text_main WHERE id = %s', (request.textId,))
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文本不存在")
        sourceText = row["sourceText"]

    errors: List[str] = []

    if not request.translatedText.strip():
        errors.append("译文不能为空")

    source_placeholders = _extract_placeholders(sourceText)
    translated_placeholders = _extract_placeholders(request.translatedText)
    if len(source_placeholders) != len(translated_placeholders):
        errors.append("花括号占位符数量不一致")

    source_percents = _extract_percent_tokens(sourceText)
    translated_percents = _extract_percent_tokens(request.translatedText)
    if len(source_percents) != len(translated_percents):
        errors.append("百分号占位符数量不一致")

    return success_response(
        {
            "valid": len(errors) == 0,
            "errors": errors,
        }
    )
