import pytest

from server.services import dictionary_correction

pytestmark = pytest.mark.no_db


def test_normalize_variant_values_accepts_json_string_from_database():
    assert dictionary_correction.normalize_variant_values('["布里", "布里", "  夏尔  "]') == ["布里", "夏尔"]


def test_normalize_variant_values_accepts_json_bytes_from_database():
    assert dictionary_correction.normalize_variant_values(b'["skill1", "skill2"]') == ["skill1", "skill2"]


def test_normalize_variant_values_rejects_invalid_json_string():
    with pytest.raises(RuntimeError, match="variantValues JSON 解析失败"):
        dictionary_correction.normalize_variant_values('["skill1"", "skill2"]')


def test_normalize_variant_values_rejects_non_string_items():
    with pytest.raises(RuntimeError, match="variantValues 第 2 项必须为字符串"):
        dictionary_correction.normalize_variant_values('["skill1", 2]')
