# 文本版本迭代 Step4: 解析 Texts.db 并生成 text_main_next 导入 SQL。

import argparse
import hashlib
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from common import (
    ConfigError,
    load_yaml_config,
    quote_ident,
    require_identifier,
    require_key,
    require_type,
)


def _validate_policy(value: str, path: str, choices: Iterable[str]) -> str:
    if value not in choices:
        joined = "/".join(choices)
        raise ConfigError(f"{path} 仅支持 {joined}")
    return value


def _validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    input_cfg = require_type(require_key(config, "input", ""), dict, "input")
    parsing_cfg = require_type(require_key(config, "parsing", ""), dict, "parsing")
    output_cfg = require_type(require_key(config, "output", ""), dict, "output")
    fixed_cfg = require_type(require_key(config, "fixedValues", ""), dict, "fixedValues")
    stats_cfg = require_type(require_key(config, "stats", ""), dict, "stats")

    sqlite_path = require_type(require_key(input_cfg, "sqlitePath", "input."), str, "input.sqlitePath")
    source_table = require_type(require_key(input_cfg, "sourceTable", "input."), str, "input.sourceTable")
    fid_column = require_type(require_key(input_cfg, "fidColumn", "input."), str, "input.fidColumn")
    text_data_column = require_type(
        require_key(input_cfg, "textDataColumn", "input."),
        str,
        "input.textDataColumn",
    )

    split_delimiter = require_type(
        require_key(parsing_cfg, "splitDelimiter", "parsing."),
        str,
        "parsing.splitDelimiter",
    )
    id_pattern = require_type(require_key(parsing_cfg, "idPattern", "parsing."), str, "parsing.idPattern")
    invalid_segment_policy = _validate_policy(
        require_type(
            require_key(parsing_cfg, "invalidSegmentPolicy", "parsing."),
            str,
            "parsing.invalidSegmentPolicy",
        ),
        "parsing.invalidSegmentPolicy",
        ("error", "skip"),
    )
    empty_text_data_policy = _validate_policy(
        require_type(
            require_key(parsing_cfg, "emptyTextDataPolicy", "parsing."),
            str,
            "parsing.emptyTextDataPolicy",
        ),
        "parsing.emptyTextDataPolicy",
        ("error", "skip"),
    )

    sql_path = require_type(require_key(output_cfg, "sqlPath", "output."), str, "output.sqlPath")
    target_table = require_type(require_key(output_cfg, "targetTable", "output."), str, "output.targetTable")
    chunk_size = require_type(require_key(output_cfg, "chunkSize", "output."), int, "output.chunkSize")
    overwrite = require_type(require_key(output_cfg, "overwrite", "output."), bool, "output.overwrite")
    columns_cfg = require_type(require_key(output_cfg, "columns", "output."), dict, "output.columns")

    translated_text = require_key(fixed_cfg, "translatedText", "fixedValues.")
    status_value = require_type(require_key(fixed_cfg, "status", "fixedValues."), int, "fixedValues.status")
    is_claimed = require_type(require_key(fixed_cfg, "isClaimed", "fixedValues."), bool, "fixedValues.isClaimed")
    edit_count = require_type(require_key(fixed_cfg, "editCount", "fixedValues."), int, "fixedValues.editCount")
    upt_time_expression = require_type(
        require_key(fixed_cfg, "uptTimeExpression", "fixedValues."),
        str,
        "fixedValues.uptTimeExpression",
    )
    crt_time_expression = require_type(
        require_key(fixed_cfg, "crtTimeExpression", "fixedValues."),
        str,
        "fixedValues.crtTimeExpression",
    )

    progress_every_fid_rows = require_type(
        require_key(stats_cfg, "progressEveryFidRows", "stats."),
        int,
        "stats.progressEveryFidRows",
    )

    if chunk_size <= 0:
        raise ConfigError("output.chunkSize 必须大于 0")
    if status_value not in (1, 2, 3):
        raise ConfigError("fixedValues.status 必须为 1/2/3")
    if edit_count < 0:
        raise ConfigError("fixedValues.editCount 不能小于 0")
    if progress_every_fid_rows < 0:
        raise ConfigError("stats.progressEveryFidRows 不能小于 0")

    for path_name, pattern_value in (("parsing.idPattern", id_pattern),):
        try:
            re.compile(pattern_value)
        except re.error as exc:
            raise ConfigError(f"{path_name} 无效: {exc}") from exc

    for name, value in (
        ("input.sourceTable", source_table),
        ("input.fidColumn", fid_column),
        ("input.textDataColumn", text_data_column),
        ("output.targetTable", target_table),
    ):
        require_identifier(value, name)

    required_columns = [
        "fid",
        "textId",
        "part",
        "sourceText",
        "sourceTextHash",
        "translatedText",
        "status",
        "isClaimed",
        "editCount",
        "uptTime",
        "crtTime",
    ]
    normalized_columns: Dict[str, str] = {}
    for key in required_columns:
        value = require_type(
            require_key(columns_cfg, key, "output.columns."),
            str,
            f"output.columns.{key}",
        )
        normalized_columns[key] = require_identifier(value, f"output.columns.{key}")

    if upt_time_expression.strip() == "" or crt_time_expression.strip() == "":
        raise ConfigError("fixedValues.uptTimeExpression/crtTimeExpression 不能为空")

    return {
        "sqlitePath": sqlite_path,
        "sourceTable": source_table,
        "fidColumn": fid_column,
        "textDataColumn": text_data_column,
        "splitDelimiter": split_delimiter,
        "idPattern": id_pattern,
        "invalidSegmentPolicy": invalid_segment_policy,
        "emptyTextDataPolicy": empty_text_data_policy,
        "sqlPath": sql_path,
        "targetTable": target_table,
        "chunkSize": chunk_size,
        "overwrite": overwrite,
        "columns": normalized_columns,
        "translatedText": translated_text,
        "status": status_value,
        "isClaimed": is_claimed,
        "editCount": edit_count,
        "uptTimeExpression": upt_time_expression,
        "crtTimeExpression": crt_time_expression,
        "progressEveryFidRows": progress_every_fid_rows,
    }


def _sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).replace("'", "''")
    return "'" + text + "'"


def _build_patterns(id_pattern: str) -> Tuple[re.Pattern[str], re.Pattern[str], re.Pattern[str]]:
    # 与 tools/valid_format/xlsx_format_check.py 的 3 种格式保持一致。
    pattern_colon6 = re.compile(
        rf"^(?P<textId>{id_pattern})::::::\[(?P<sourceText>.*)\]$",
        re.DOTALL,
    )
    pattern_triple_colon_num = re.compile(
        rf"^(?P<textId>{id_pattern}):::\d+:::\[(?P<sourceText>.*)\]$",
        re.DOTALL,
    )
    pattern_triple_colon_range = re.compile(
        rf"^(?P<textId>{id_pattern}):::\d+(?:-\d+)+:::\[(?P<sourceText>.*)\]$",
        re.DOTALL,
    )
    return pattern_colon6, pattern_triple_colon_num, pattern_triple_colon_range


def _parse_segment(
    segment: str,
    patterns: Tuple[re.Pattern[str], re.Pattern[str], re.Pattern[str]],
) -> Optional[Tuple[int, str]]:
    pattern_colon6, pattern_triple_colon_num, pattern_triple_colon_range = patterns
    matched = (
        pattern_colon6.fullmatch(segment)
        or pattern_triple_colon_num.fullmatch(segment)
        or pattern_triple_colon_range.fullmatch(segment)
    )
    if matched is None:
        return None
    return int(matched.group("textId")), matched.group("sourceText")


def _write_insert_sql(handle, table_name: str, columns: List[str], rows: List[List[str]]) -> None:
    if not rows:
        return
    columns_sql = ", ".join(quote_ident(column_name) for column_name in columns)
    handle.write(f"INSERT INTO {quote_ident(table_name)} ({columns_sql}) VALUES\n")
    for idx, row in enumerate(rows):
        suffix = ",\n" if idx < len(rows) - 1 else ";\n"
        handle.write("(" + ", ".join(row) + ")" + suffix)


def main() -> None:
    parser = argparse.ArgumentParser(description="Step4 生成 text_main_next 导入 SQL")
    parser.add_argument("--config", required=True, help="配置文件路径")
    args = parser.parse_args()

    config = _validate_config(load_yaml_config(Path(args.config).expanduser().resolve()))

    sqlite_path = Path(config["sqlitePath"]).expanduser().resolve()
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite 文件不存在: {sqlite_path}")

    output_path = Path(config["sqlPath"]).expanduser().resolve()
    if output_path.exists() and not config["overwrite"]:
        raise RuntimeError(f"输出文件已存在且 overwrite=false: {output_path}")
    if not output_path.parent.exists():
        raise FileNotFoundError(f"输出目录不存在: {output_path.parent}")

    patterns = _build_patterns(config["idPattern"])

    ordered_columns = [
        config["columns"]["fid"],
        config["columns"]["textId"],
        config["columns"]["part"],
        config["columns"]["sourceText"],
        config["columns"]["sourceTextHash"],
        config["columns"]["translatedText"],
        config["columns"]["status"],
        config["columns"]["isClaimed"],
        config["columns"]["editCount"],
        config["columns"]["uptTime"],
        config["columns"]["crtTime"],
    ]

    select_sql = (
        f"SELECT {quote_ident(config['fidColumn'])}, {quote_ident(config['textDataColumn'])} "
        f"FROM {quote_ident(config['sourceTable'])} ORDER BY {quote_ident(config['fidColumn'])}"
    )

    total_fid_rows = 0
    skipped_empty_rows = 0
    total_segments = 0
    valid_segments = 0

    rows_buffer: List[List[str]] = []

    with sqlite3.connect(sqlite_path) as conn:
        cursor = conn.cursor()
        cursor.execute(select_sql)

        with output_path.open("w", encoding="utf-8") as handle:
            handle.write("-- Auto-generated by step4_generate_text_main_next_insert.py\n")
            handle.write(f"-- generated_at_utc: {datetime.now(timezone.utc).isoformat()}\n")
            handle.write(f"-- source_sqlite: {sqlite_path}\n\n")

            for fid_raw, text_data_raw in cursor:
                total_fid_rows += 1
                if config["progressEveryFidRows"] > 0 and total_fid_rows % config["progressEveryFidRows"] == 0:
                    print(f"[PROGRESS] fid_rows={total_fid_rows}, valid_segments={valid_segments}")

                fid_value = str(fid_raw)
                text_data = "" if text_data_raw is None else str(text_data_raw)

                if text_data == "":
                    if config["emptyTextDataPolicy"] == "skip":
                        skipped_empty_rows += 1
                        continue
                    raise RuntimeError(f"text_data 为空: fid={fid_value}")

                part = 0
                for segment_index, raw_segment in enumerate(text_data.split(config["splitDelimiter"]), start=1):
                    total_segments += 1
                    segment = raw_segment.strip()
                    if segment == "":
                        if config["invalidSegmentPolicy"] == "skip":
                            continue
                        raise RuntimeError(f"空分段: fid={fid_value}, segmentIndex={segment_index}")

                    parsed = _parse_segment(segment, patterns)
                    if parsed is None:
                        if config["invalidSegmentPolicy"] == "skip":
                            continue
                        preview = segment[:200]
                        raise RuntimeError(
                            f"分段格式不合法: fid={fid_value}, segmentIndex={segment_index}, segment={preview}"
                        )

                    text_id, source_text = parsed
                    source_hash = hashlib.sha256(source_text.encode("utf-8")).hexdigest()

                    part += 1
                    valid_segments += 1
                    rows_buffer.append(
                        [
                            _sql_literal(fid_value),
                            _sql_literal(text_id),
                            _sql_literal(part),
                            _sql_literal(source_text),
                            _sql_literal(source_hash),
                            _sql_literal(config["translatedText"]),
                            _sql_literal(config["status"]),
                            _sql_literal(config["isClaimed"]),
                            _sql_literal(config["editCount"]),
                            config["uptTimeExpression"],
                            config["crtTimeExpression"],
                        ]
                    )

                    if len(rows_buffer) >= config["chunkSize"]:
                        _write_insert_sql(handle, config["targetTable"], ordered_columns, rows_buffer)
                        rows_buffer = []

            if rows_buffer:
                _write_insert_sql(handle, config["targetTable"], ordered_columns, rows_buffer)

            handle.write("\n")
            handle.write(f"-- total_fid_rows: {total_fid_rows}\n")
            handle.write(f"-- skipped_empty_rows: {skipped_empty_rows}\n")
            handle.write(f"-- total_segments: {total_segments}\n")
            handle.write(f"-- valid_segments: {valid_segments}\n")

    print("[DONE] Step4 导入 SQL 生成完成")
    print(f"[STAT] total_fid_rows={total_fid_rows}")
    print(f"[STAT] skipped_empty_rows={skipped_empty_rows}")
    print(f"[STAT] total_segments={total_segments}")
    print(f"[STAT] valid_segments={valid_segments}")
    print(f"[FILE] {output_path}")


if __name__ == "__main__":
    main()
