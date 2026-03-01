# 文本模板上传校验的纯逻辑测试（不依赖数据库）。
import pytest
from fastapi import HTTPException

from server.routes.texts import _parse_required_int, _parse_required_str, _parse_status, _validate_template_header


pytestmark = pytest.mark.no_db


def test_validate_template_header_success():
    _validate_template_header(["编号", "FID", "TextId", "Part", "原文", "译文", "状态"])


def test_validate_template_header_mismatch():
    with pytest.raises(HTTPException) as error:
        _validate_template_header(["编号", "FID", "TextID", "Part", "原文", "译文", "状态"])
    assert error.value.status_code == 400
    assert "表头不匹配" in str(error.value.detail)


def test_parse_status_with_chinese_label():
    assert _parse_status("新增", 2) == 1
    assert _parse_status("修改", 2) == 2
    assert _parse_status("已完成", 2) == 3


def test_parse_status_with_invalid_value():
    with pytest.raises(HTTPException) as error:
        _parse_status("完成", 3)
    assert error.value.status_code == 400
    assert "状态 非法" in str(error.value.detail)


def test_parse_required_int_and_str():
    assert _parse_required_int("12", "编号", 4) == 12
    assert _parse_required_int(12.0, "编号", 4) == 12
    assert _parse_required_str("file_a", "FID", 4) == "file_a"


def test_parse_required_int_reject_bool_and_empty():
    with pytest.raises(HTTPException):
        _parse_required_int(True, "编号", 5)
    with pytest.raises(HTTPException):
        _parse_required_int("", "编号", 5)
