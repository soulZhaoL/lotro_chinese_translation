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


def test_count_non_overlapping_occurrences():
    assert dictionary_correction._count_non_overlapping_occurrences("Bree Bree Bree", "Bree") == 3
    assert dictionary_correction._count_non_overlapping_occurrences("aaaa", "aa") == 2


def test_build_text_correction_analysis_matches_counts_and_replaces_variants():
    result = dictionary_correction._build_text_correction_analysis(
        "Bree-pony from Bree",
        "布里小马回到布里",
        "Bree",
        ["布里"],
        "布雷",
    )
    assert result.source_match_count == 2
    assert result.translated_match_count == 2
    assert result.after_text == "布雷小马回到布雷"


def test_build_text_correction_analysis_uses_longest_variant_first():
    result = dictionary_correction._build_text_correction_analysis(
        "Bree Bree",
        "布里镇和布里",
        "Bree",
        ["布里", "布里镇"],
        "布雷",
    )
    assert result.source_match_count == 2
    assert result.translated_match_count == 2
    assert result.after_text == "布雷和布雷"
