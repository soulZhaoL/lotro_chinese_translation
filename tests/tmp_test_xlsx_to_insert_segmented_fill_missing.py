import pytest

from tools.valid_format.xlsx_to_insert_segmented import (
    RowParseError,
    _build_output_rows_for_excel_row,
    _build_patterns,
    _fill_missing_translated_segments,
)


pytestmark = pytest.mark.no_db


def test_fill_missing_translated_segments_copies_missing_source_segments():
    source_segments = [
        ("10001", "src_a"),
        ("10002", "src_b"),
        ("10003", "src_c"),
    ]
    translated_segments = [
        ("10001", "dst_a"),
        ("10003", "dst_c"),
    ]

    aligned, copied_count, dropped_count = _fill_missing_translated_segments(
        fid="620757423",
        row_index=408,
        source_segments=source_segments,
        translated_segments=translated_segments,
    )

    assert copied_count == 1
    assert dropped_count == 0
    assert aligned == [
        ("10001", "dst_a"),
        ("10002", "src_b"),
        ("10003", "dst_c"),
    ]


def test_fill_missing_translated_segments_drops_unmatched_extra_segment():
    source_segments = [
        ("10001", "src_a"),
        ("10002", "src_b"),
    ]
    translated_segments = [
        ("99999", "dst_x"),
        ("10001", "dst_a"),
    ]

    aligned, copied_count, dropped_count = _fill_missing_translated_segments(
        fid="620757716",
        row_index=689,
        source_segments=source_segments,
        translated_segments=translated_segments,
    )

    assert copied_count == 1
    assert dropped_count == 1
    assert aligned == [
        ("10001", "dst_a"),
        ("10002", "src_b"),
    ]


def test_fill_missing_translated_segments_reorders_by_source_order_with_copy():
    source_segments = [
        ("218649170", "src_1"),
        ("218649171", "src_2"),
        ("228870261", "src_3"),
        ("218649172", "src_4"),
    ]
    translated_segments = [
        ("218649170", "dst_1"),
        ("228870261", "dst_3"),
        ("218649171", "dst_2"),
        ("218649172", "dst_4"),
    ]

    aligned, copied_count, dropped_count = _fill_missing_translated_segments(
        fid="620757716",
        row_index=689,
        source_segments=source_segments,
        translated_segments=translated_segments,
    )

    assert copied_count == 1
    assert dropped_count == 1
    assert aligned == [
        ("218649170", "dst_1"),
        ("218649171", "src_2"),
        ("228870261", "dst_3"),
        ("218649172", "dst_4"),
    ]


def test_build_output_rows_fills_missing_translated_segment_with_source_text():
    patterns = _build_patterns(r"\d{2,10}")

    rows = _build_output_rows_for_excel_row(
        fid="620757423",
        source_raw="10001::::::[src_a]|||10002::::::[src_b]|||10003::::::[src_c]",
        translated_raw="10001::::::[dst_a]|||10003::::::[dst_c]",
        split_delimiter="|||",
        patterns=patterns,
        row_index=408,
        status_value=1,
        is_claimed_value=False,
    )

    assert len(rows) == 3
    assert rows[0][2] == "'10001'"
    assert rows[0][5] == "'dst_a'"
    assert rows[1][2] == "'10002'"
    assert rows[1][5] == "'src_b'"
    assert rows[2][2] == "'10003'"
    assert rows[2][5] == "'dst_c'"


def test_build_output_rows_realigns_equal_count_textid_mismatch_by_source_order():
    patterns = _build_patterns(r"\d{2,10}")

    rows = _build_output_rows_for_excel_row(
        fid="620757716",
        source_raw="10001::::::[src_a]|||10002::::::[src_b]",
        translated_raw="10002::::::[dst_b]|||10001::::::[dst_a]",
        split_delimiter="|||",
        patterns=patterns,
        row_index=689,
        status_value=1,
        is_claimed_value=False,
    )

    assert len(rows) == 2
    assert rows[0][2] == "'10001'"
    assert rows[0][5] == "'src_a'"
    assert rows[1][2] == "'10002'"
    assert rows[1][5] == "'dst_b'"
