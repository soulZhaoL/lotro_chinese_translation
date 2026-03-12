"""从 SQLite 原始数据推导 textId 错误→正确映射，生成 UPDATE SQL。

原理：
  对同一条分段，分别用"旧错误正则"和"新正确正则"各提取一次 textId，
  找出两者不一致的条目，建立 (fid, old_textId) → new_textId 映射，
  无需连接数据库，直接生成可执行的 UPDATE SQL。

旧正则（错误方式，复现当时导入时的行为）：
  格式1 {num}::::::[text]        → textId = {num}         ← 无需修复
  格式2 {num}:::{n}:::[text]     → textId = {num}         ← 错误（丢失 :::{n}）
  格式3 {num}:::{m-n}:::[text]   → textId = {num}         ← 错误（丢失 :::{m-n}）

新正则（正确方式）：
  格式1 {num}::::::[text]        → textId = {num}         ← 同上，无需修复
  格式2 {num}:::{n}:::[text]     → textId = {num}:::{n}   ← 正确
  格式3 {num}:::{m-n}:::[text]   → textId = {num}:::{m-n} ← 正确

用法:
  python tools/fix_textid/generate_fix_sql_from_sqlite.py --config tools/fix_textid/generate_fix_sql_from_sqlite.yaml
"""

import argparse
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

_TOOLS_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_TOOLS_ROOT / "version_iteration_tool"))

from common import ConfigError, load_yaml_config, require_key, require_type  # noqa: E402


def _validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    input_cfg = require_type(require_key(config, "input", ""), dict, "input")
    parsing_cfg = require_type(require_key(config, "parsing", ""), dict, "parsing")
    output_cfg = require_type(require_key(config, "output", ""), dict, "output")
    db_cfg = require_type(require_key(config, "db", ""), dict, "db")

    sqlite_path = require_type(require_key(input_cfg, "sqlitePath", "input."), str, "input.sqlitePath")
    source_table = require_type(require_key(input_cfg, "sourceTable", "input."), str, "input.sourceTable")
    fid_column = require_type(require_key(input_cfg, "fidColumn", "input."), str, "input.fidColumn")
    text_data_column = require_type(
        require_key(input_cfg, "textDataColumn", "input."), str, "input.textDataColumn"
    )

    split_delimiter = require_type(
        require_key(parsing_cfg, "splitDelimiter", "parsing."), str, "parsing.splitDelimiter"
    )
    id_pattern = require_type(require_key(parsing_cfg, "idPattern", "parsing."), str, "parsing.idPattern")
    try:
        re.compile(id_pattern)
    except re.error as exc:
        raise ConfigError(f"parsing.idPattern 无效: {exc}") from exc

    csv_path = require_type(require_key(output_cfg, "csvPath", "output."), str, "output.csvPath")
    sql_path = require_type(require_key(output_cfg, "sqlPath", "output."), str, "output.sqlPath")
    overwrite = require_type(require_key(output_cfg, "overwrite", "output."), bool, "output.overwrite")

    db_table = require_type(require_key(db_cfg, "table", "db."), str, "db.table")

    if split_delimiter == "":
        raise ConfigError("parsing.splitDelimiter 不能为空")

    return {
        "sqlitePath": sqlite_path,
        "sourceTable": source_table,
        "fidColumn": fid_column,
        "textDataColumn": text_data_column,
        "splitDelimiter": split_delimiter,
        "idPattern": id_pattern,
        "csvPath": csv_path,
        "sqlPath": sql_path,
        "overwrite": overwrite,
        "dbTable": db_table,
    }


def _build_wrong_patterns(
    id_pattern: str,
) -> Tuple[re.Pattern[str], re.Pattern[str], re.Pattern[str]]:
    """构建旧的（错误的）正则——复现导入时的行为。
    格式2/3 的 textId 命名组只捕获数字前缀，不含 :::{n} 或 :::{m-n} 部分。
    """
    p1 = re.compile(rf"^(?P<textId>{id_pattern})::::::\[(?P<text>.*)\]$", re.DOTALL)
    p2 = re.compile(rf"^(?P<textId>{id_pattern}):::\d+:::\[(?P<text>.*)\]$", re.DOTALL)
    p3 = re.compile(rf"^(?P<textId>{id_pattern}):::\d+(?:-\d+)+:::\[(?P<text>.*)\]$", re.DOTALL)
    return p1, p2, p3


def _build_correct_patterns(
    id_pattern: str,
) -> Tuple[re.Pattern[str], re.Pattern[str], re.Pattern[str]]:
    """构建新的（正确的）正则。
    格式2/3 的 textId 命名组包含完整业务标识。
    """
    p1 = re.compile(rf"^(?P<textId>{id_pattern})::::::\[(?P<text>.*)\]$", re.DOTALL)
    p2 = re.compile(rf"^(?P<textId>{id_pattern}:::\d+):::\[(?P<text>.*)\]$", re.DOTALL)
    p3 = re.compile(
        rf"^(?P<textId>{id_pattern}:::\d+(?:-\d+)+):::\[(?P<text>.*)\]$", re.DOTALL
    )
    return p1, p2, p3


def _extract_textid(
    segment: str,
    patterns: Tuple[re.Pattern[str], re.Pattern[str], re.Pattern[str]],
) -> Optional[str]:
    """从一条分段文本中提取 textId，三个格式按顺序尝试，返回 None 表示格式无法识别。"""
    for p in patterns:
        m = p.fullmatch(segment)
        if m:
            return m.group("textId")
    return None


def _scan_sqlite(
    config: Dict[str, Any],
    wrong_patterns: Tuple[re.Pattern[str], re.Pattern[str], re.Pattern[str]],
    correct_patterns: Tuple[re.Pattern[str], re.Pattern[str], re.Pattern[str]],
) -> Dict[Tuple[str, str], str]:
    """扫描 SQLite 数据，建立 (fid, old_textId) → new_textId 映射。
    只包含需要修复的条目（old_textId != new_textId）。
    """
    sqlite_path = Path(config["sqlitePath"]).expanduser().resolve()
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite 文件不存在: {sqlite_path}")

    fix_map: Dict[Tuple[str, str], str] = {}
    total_fid_rows = 0
    total_segments = 0
    skipped_segments = 0

    select_sql = (
        f'SELECT "{config["fidColumn"]}", "{config["textDataColumn"]}" '
        f'FROM "{config["sourceTable"]}" ORDER BY "{config["fidColumn"]}"'
    )

    with sqlite3.connect(sqlite_path) as conn:
        cursor = conn.cursor()
        cursor.execute(select_sql)
        for fid_raw, text_data_raw in cursor:
            total_fid_rows += 1
            fid = str(fid_raw)
            text_data = "" if text_data_raw is None else str(text_data_raw)
            if text_data == "":
                continue

            for raw_segment in text_data.split(config["splitDelimiter"]):
                segment = raw_segment.strip()
                if segment == "":
                    continue
                total_segments += 1

                old_tid = _extract_textid(segment, wrong_patterns)
                new_tid = _extract_textid(segment, correct_patterns)

                if old_tid is None or new_tid is None:
                    skipped_segments += 1
                    continue

                # 格式1：旧/新 textId 相同，无需修复
                if old_tid == new_tid:
                    continue

                key = (fid, old_tid)
                if key in fix_map:
                    if fix_map[key] != new_tid:
                        raise RuntimeError(
                            f"映射冲突: fid={fid}, old_textId={old_tid} "
                            f"映射到了不同的 new_textId: {fix_map[key]!r} vs {new_tid!r}"
                        )
                else:
                    fix_map[key] = new_tid

    print(
        f"[INFO] SQLite 扫描完成: fid_rows={total_fid_rows}, "
        f"segments={total_segments}, skipped(格式未识别)={skipped_segments}"
    )
    print(f"[INFO] 需要修复的 (fid, textId) 条目: {len(fix_map)} 条")
    return fix_map


def _sql_escape(value: str) -> str:
    """MySQL 字符串字面量转义（单引号包裹）。"""
    value = value.replace("\\", "\\\\")
    value = value.replace("'", "''")
    return "'" + value + "'"


_INSERT_CHUNK_SIZE = 1000  # 每个 INSERT 语句最多包含的行数


def _write_outputs(fix_map: Dict[Tuple[str, str], str], config: Dict[str, Any], source_label: str) -> None:
    """将修复映射写出为 CSV 和 UPDATE SQL。
    SQL 格式：临时表 + JOIN UPDATE，一次性批量执行，避免逐条 fsync 开销。
    """
    csv_path = Path(config["csvPath"]).expanduser().resolve()
    sql_path = Path(config["sqlPath"]).expanduser().resolve()
    db_table = config["dbTable"]
    now_str = datetime.now(timezone.utc).isoformat()

    sorted_entries = sorted(fix_map.items(), key=lambda x: (x[0][0], x[0][1]))

    with csv_path.open("w", encoding="utf-8") as f:
        f.write("fid,old_textId,new_textId\n")
        for (fid, old_tid), new_tid in sorted_entries:
            fid_esc = fid.replace('"', '""')
            old_esc = old_tid.replace('"', '""')
            new_esc = new_tid.replace('"', '""')
            f.write(f'"{fid_esc}","{old_esc}","{new_esc}"\n')
    print(f"[FILE] CSV: {csv_path}")

    with sql_path.open("w", encoding="utf-8") as f:
        f.write("-- Auto-generated by generate_fix_sql_from_sqlite.py\n")
        f.write(f"-- generated_at_utc: {now_str}\n")
        f.write(f"-- source: {source_label}\n")
        f.write(f"-- total_fix_entries: {len(fix_map)}\n\n")

        # 1. 创建临时表
        f.write("CREATE TEMPORARY TABLE `_textid_fix` (\n")
        f.write("  `fid` VARCHAR(64) NOT NULL,\n")
        f.write("  `old_textId` VARCHAR(200) NOT NULL,\n")
        f.write("  `new_textId` VARCHAR(200) NOT NULL,\n")
        f.write("  PRIMARY KEY (`fid`, `old_textId`)\n")
        f.write(") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;\n\n")

        # 2. 分批 INSERT（每批 _INSERT_CHUNK_SIZE 行，避免单条 SQL 过长）
        for i in range(0, len(sorted_entries), _INSERT_CHUNK_SIZE):
            chunk = sorted_entries[i : i + _INSERT_CHUNK_SIZE]
            f.write("INSERT INTO `_textid_fix` (`fid`, `old_textId`, `new_textId`) VALUES\n")
            for j, ((fid, old_tid), new_tid) in enumerate(chunk):
                suffix = "," if j < len(chunk) - 1 else ";"
                f.write(
                    f"  ({_sql_escape(fid)}, {_sql_escape(old_tid)}, {_sql_escape(new_tid)}){suffix}\n"
                )
            f.write("\n")

        # 3. 一次 JOIN UPDATE 批量修复（走 (fid, old_textId) 联合主键，极快）
        f.write(f"UPDATE `{db_table}` t\n")
        f.write("  JOIN `_textid_fix` m ON t.`fid` = m.`fid` AND t.`textId` = m.`old_textId`\n")
        f.write("  SET t.`textId` = m.`new_textId`;\n\n")

        # 4. 清理临时表
        f.write("DROP TEMPORARY TABLE `_textid_fix`;\n")
    print(f"[FILE] SQL: {sql_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="从 SQLite 原始数据推导 textId 修复映射，生成 UPDATE SQL（无需连接数据库）"
    )
    parser.add_argument("--config", required=True, help="配置文件路径")
    args = parser.parse_args()

    config_path = Path(args.config).expanduser().resolve()
    config = _validate_config(load_yaml_config(config_path))

    csv_path = Path(config["csvPath"]).expanduser().resolve()
    sql_path = Path(config["sqlPath"]).expanduser().resolve()
    for out_path in (csv_path, sql_path):
        if out_path.exists() and not config["overwrite"]:
            raise RuntimeError(f"输出文件已存在且 overwrite=false: {out_path}")
        if not out_path.parent.exists():
            raise FileNotFoundError(f"输出目录不存在: {out_path.parent}")

    wrong_patterns = _build_wrong_patterns(config["idPattern"])
    correct_patterns = _build_correct_patterns(config["idPattern"])

    fix_map = _scan_sqlite(config, wrong_patterns, correct_patterns)
    _write_outputs(fix_map, config, source_label=config["sqlitePath"])

    print("[DONE] 修复映射生成完成")
    print(f"[STAT] total_fix_entries={len(fix_map)}")


if __name__ == "__main__":
    main()
    # python tools/fix_textid/generate_fix_sql_from_sqlite.py --config tools/fix_textid/generate_fix_sql_from_sqlite.yaml
