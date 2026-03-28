from pathlib import Path

import pytest
import yaml
from openpyxl import Workbook

from tools.xlsx_compare.compare_translation_by_fid import ConfigError, load_config, XlsxTranslationComparer


def _build_workbook(path: Path, rows: list[tuple]):
    workbook = Workbook()
    worksheet = workbook.active
    for row in rows:
        worksheet.append(list(row))
    workbook.save(path)


@pytest.mark.no_db
def test_compare_translation_after_grouping_by_fid(tmp_path: Path):
    left_path = tmp_path / "left.xlsx"
    right_path = tmp_path / "right.xlsx"
    report_path = tmp_path / "tmp_report.csv"
    summary_path = tmp_path / "tmp_summary.txt"
    config_path = tmp_path / "tmp_config.yaml"

    _build_workbook(
        left_path,
        [
            ("fid", "split_part", "translation"),
            ("100", 2, "B"),
            ("100", 1, "A"),
            ("200", 1, "X"),
        ],
    )
    _build_workbook(
        right_path,
        [
            ("fid", "translation"),
            ("100", "AB"),
            ("200", "Y"),
        ],
    )

    config_path.write_text(
        yaml.safe_dump(
            {
                "base_dir": str(tmp_path),
                "files": {
                    "left": {
                        "path": "left.xlsx",
                        "sheet": "Sheet",
                        "header_row": 1,
                        "data_start_row": 2,
                        "key_column": "fid",
                        "compare_column": "translation",
                        "order": {
                            "mode": "column",
                            "column": "split_part",
                            "value_type": "int",
                            "require_unique": True,
                        },
                    },
                    "right": {
                        "path": "right.xlsx",
                        "sheet": "Sheet",
                        "header_row": 1,
                        "data_start_row": 2,
                        "key_column": "fid",
                        "compare_column": "translation",
                        "order": {
                            "mode": "document",
                        },
                    },
                },
                "output": {
                    "report_path": "tmp_report.csv",
                    "summary_path": "tmp_summary.txt",
                },
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    left_cfg, right_cfg, loaded_report_path, loaded_summary_path = load_config(config_path)
    comparer = XlsxTranslationComparer(left_cfg, right_cfg, loaded_report_path, loaded_summary_path)
    exit_code = comparer.run()

    assert exit_code == 1
    summary_text = summary_path.read_text(encoding="utf-8")
    assert "translation_mismatch_fid=1" in summary_text
    report_text = report_path.read_text(encoding="utf-8")
    assert "translation_mismatch,200,1,1,X,Y" in report_text


@pytest.mark.no_db
def test_compare_translation_detects_duplicate_sort_value(tmp_path: Path):
    left_path = tmp_path / "left.xlsx"
    right_path = tmp_path / "right.xlsx"
    config_path = tmp_path / "tmp_config.yaml"

    _build_workbook(
        left_path,
        [
            ("fid", "split_part", "translation"),
            ("100", 1, "A"),
            ("100", 1, "B"),
        ],
    )
    _build_workbook(
        right_path,
        [
            ("fid", "translation"),
            ("100", "AB"),
        ],
    )

    config_path.write_text(
        yaml.safe_dump(
            {
                "base_dir": str(tmp_path),
                "files": {
                    "left": {
                        "path": "left.xlsx",
                        "sheet": "Sheet",
                        "header_row": 1,
                        "data_start_row": 2,
                        "key_column": "fid",
                        "compare_column": "translation",
                        "order": {
                            "mode": "column",
                            "column": "split_part",
                            "value_type": "int",
                            "require_unique": True,
                        },
                    },
                    "right": {
                        "path": "right.xlsx",
                        "sheet": "Sheet",
                        "header_row": 1,
                        "data_start_row": 2,
                        "key_column": "fid",
                        "compare_column": "translation",
                        "order": {
                            "mode": "document",
                        },
                    },
                },
                "output": {
                    "report_path": "tmp_report.csv",
                    "summary_path": "tmp_summary.txt",
                },
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    left_cfg, right_cfg, report_path, summary_path = load_config(config_path)
    comparer = XlsxTranslationComparer(left_cfg, right_cfg, report_path, summary_path)

    with pytest.raises(ConfigError, match="存在重复值"):
        comparer.run()
