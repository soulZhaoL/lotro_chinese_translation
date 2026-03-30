# 分段协议正则与结构校验测试。

from tools.valid_format.xlsx_to_insert_segmented import (
    RowParseError,
    _build_output_rows_for_excel_row,
    _build_patterns as build_valid_patterns,
    _parse_segment as parse_valid_segment,
)
from tools.version_iteration_tool.step4_generate_text_main_next_insert import (
    _build_patterns as build_step4_patterns,
    _parse_segment as parse_step4_segment,
    _validate_segment_text_structure,
)


def test_valid_format_parser_keeps_full_textid_for_triple_colon_range():
    patterns = build_valid_patterns(r"\d{2,10}")
    segment = (
        "235705092:::337429-5021188:::[#1:<--DO_NOT_TOUCH!-->邀请你加入"
        "#1:{她[f]|他[m]}的家族，#2:<--DO_NOT_TOUCH!-->。你接受吗？]"
    )

    parsed = parse_valid_segment(segment, patterns)

    assert parsed == (
        "235705092:::337429-5021188",
        "#1:<--DO_NOT_TOUCH!-->邀请你加入#1:{她[f]|他[m]}的家族，#2:<--DO_NOT_TOUCH!-->。你接受吗？",
    )


def test_step4_parser_keeps_full_textid_for_triple_colon_range():
    patterns = build_step4_patterns(r"\d{2,10}")
    segment = (
        "235705092:::337429-5021188:::[#1:<--DO_NOT_TOUCH!-->邀请你加入"
        "#1:{她[f]|他[m]}的家族，#2:<--DO_NOT_TOUCH!-->。你接受吗？]"
    )

    parsed = parse_step4_segment(segment, patterns)

    assert parsed == (
        "235705092:::337429-5021188",
        "#1:<--DO_NOT_TOUCH!-->邀请你加入#1:{她[f]|他[m]}的家族，#2:<--DO_NOT_TOUCH!-->。你接受吗？",
    )


def test_valid_format_rejects_unbalanced_braces_in_segment_text():
    patterns = build_valid_patterns(r"\d{2,10}")
    bad_translation = "235705092:::337429-5021188:::[#1:<--DO_NOT_TOUCH!-->邀请你加入#1:{她[f]]"

    try:
        _build_output_rows_for_excel_row(
            fid="620757429",
            source_raw=bad_translation,
            translated_raw=bad_translation,
            split_delimiter="|||",
            patterns=patterns,
            row_index=2,
            status_value=1,
            is_claimed_value=False,
        )
    except RowParseError as exc:
        assert "content invalid" in str(exc)
        assert "unbalanced {}" in str(exc)
    else:
        raise AssertionError("expected RowParseError for malformed segment")


def test_step4_structure_validator_rejects_unbalanced_braces():
    text = "#1:<--DO_NOT_TOUCH!-->邀请你加入#1:{她[f]"

    error = _validate_segment_text_structure(text)

    assert error == "unbalanced {}: open=1, close=0"
