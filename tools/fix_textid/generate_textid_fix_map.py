# 修复映射生成工具：扫描存量数据库中错误（整型截断）的 textId，生成对照 CSV 与 UPDATE SQL。
# 使用场景：系统上线时 text_main.textId 曾以 int() 截断存储，此脚本找出所有需要纠正的记录。

import argparse
import hashlib
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 引入版本迭代工具的公共模块
_TOOLS_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_TOOLS_ROOT / "version_iteration_tool"))

from common import (  # noqa: E402
    ConfigError,
    connect_mysql_from_dsn,
    load_env_file,
    load_yaml_config,
    require_key,
    require_type,
)


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
    dsn_env = require_type(require_key(db_cfg, "dsnEnv", "db."), str, "db.dsnEnv")

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
        "dsnEnv": dsn_env,
    }


def _build_patterns(id_pattern: str) -> Tuple[re.Pattern, re.Pattern, re.Pattern]:
    # textId 命名组必须包含完整业务标识：
    #   格式1 {num}::::::[text]        → textId = {num}
    #   格式2 {num}:::{n}:::[text]     → textId = {num}:::{n}
    #   格式3 {num}:::{m-n}:::[text]   → textId = {num}:::{m-n}
    pattern_colon6 = re.compile(
        rf"^(?P<textId>{id_pattern})::::::\[(?P<sourceText>.*)\]$",
        re.DOTALL,
    )
    pattern_triple_colon_num = re.compile(
        rf"^(?P<textId>{id_pattern}:::\d+):::\[(?P<sourceText>.*)\]$",
        re.DOTALL,
    )
    pattern_triple_colon_range = re.compile(
        rf"^(?P<textId>{id_pattern}:::\d+(?:-\d+)+):::\[(?P<sourceText>.*)\]$",
        re.DOTALL,
    )
    return pattern_colon6, pattern_triple_colon_num, pattern_triple_colon_range


def _parse_segment(
    segment: str,
    patterns: Tuple[re.Pattern, re.Pattern, re.Pattern],
) -> Optional[Tuple[str, str]]:
    pattern_colon6, pattern_triple_colon_num, pattern_triple_colon_range = patterns
    matched = (
        pattern_colon6.fullmatch(segment)
        or pattern_triple_colon_num.fullmatch(segment)
        or pattern_triple_colon_range.fullmatch(segment)
    )
    if matched is None:
        return None
    text = matched.group("sourceText")
    open_count = text.count("[")
    close_count = text.count("]")
    if open_count > close_count:
        text = text + "]" * (open_count - close_count)
    return matched.group("textId"), text


def _load_source_index(config: Dict[str, Any]) -> Dict[Tuple[str, int, str], str]:
    """
    解析 SQLite 源数据，以 (fid, part, sourceTextHash) 为键，映射到正确的字符串 textId。
    """
    sqlite_path = Path(config["sqlitePath"]).expanduser().resolve()
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite 文件不存在: {sqlite_path}")

    patterns = _build_patterns(config["idPattern"])
    index: Dict[Tuple[str, int, str], str] = {}

    select_sql = (
        f"SELECT \"{config['fidColumn']}\", \"{config['textDataColumn']}\" "
        f"FROM \"{config['sourceTable']}\" ORDER BY \"{config['fidColumn']}\""
    )

    total_fid_rows = 0
    total_valid = 0

    with sqlite3.connect(sqlite_path) as conn:
        cursor = conn.cursor()
        cursor.execute(select_sql)
        for fid_raw, text_data_raw in cursor:
            total_fid_rows += 1
            fid_value = str(fid_raw)
            text_data = "" if text_data_raw is None else str(text_data_raw)
            if text_data == "":
                continue

            part = 0
            for raw_segment in text_data.split(config["splitDelimiter"]):
                segment = raw_segment.strip()
                if segment == "":
                    continue
                parsed = _parse_segment(segment, patterns)
                if parsed is None:
                    continue
                text_id, source_text = parsed
                source_hash = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
                part += 1
                key = (fid_value, part, source_hash)
                if key in index:
                    print(f"[WARN] SQLite 中存在重复 key: fid={fid_value}, part={part}, hash={source_hash[:8]}...")
                index[key] = text_id
                total_valid += 1

    print(f"[INFO] SQLite 解析完成: fid_rows={total_fid_rows}, valid_segments={total_valid}")
    return index


def _escape_sql_string(value: str) -> str:
    value = value.replace("\\", "\\\\")
    value = value.replace("'", "''")
    return "'" + value + "'"


def main() -> None:
    parser = argparse.ArgumentParser(description="生成存量 textId 错误→正确的修复映射")
    parser.add_argument("--config", required=True, help="配置文件路径")
    parser.add_argument(
        "--use-ssh-tunnel",
        action="store_true",
        help="使用 SSH 隧道连接数据库",
    )
    args = parser.parse_args()

    config = _validate_config(load_yaml_config(Path(args.config).expanduser().resolve()))

    csv_path = Path(config["csvPath"]).expanduser().resolve()
    sql_path = Path(config["sqlPath"]).expanduser().resolve()
    for out_path in (csv_path, sql_path):
        if out_path.exists() and not config["overwrite"]:
            raise RuntimeError(f"输出文件已存在且 overwrite=false: {out_path}")
        if not out_path.parent.exists():
            raise FileNotFoundError(f"输出目录不存在: {out_path.parent}")

    # 1. 解析 SQLite 源数据，建立 (fid, part, hash) → correct_textId 索引
    source_index = _load_source_index(config)

    # 2. 连接 MySQL，读取所有存量记录
    import os

    load_env_file()
    dsn = os.environ.get(config["dsnEnv"])
    if not dsn:
        raise RuntimeError(f"缺少环境变量: {config['dsnEnv']}")

    db_table = config["dbTable"]

    def run_query(conn) -> List[Dict]:
        with conn.cursor() as cursor:
            cursor.execute(
                f'SELECT `id`, `fid`, `textId`, `part`, `sourceTextHash` FROM `{db_table}`'
            )
            return cursor.fetchall()

    if args.use_ssh_tunnel:
        from common import start_ssh_tunnel_from_env  # noqa: F401
        with start_ssh_tunnel_from_env():
            conn = connect_mysql_from_dsn(dsn)
            try:
                db_rows = run_query(conn)
            finally:
                conn.close()
    else:
        conn = connect_mysql_from_dsn(dsn)
        try:
            db_rows = run_query(conn)
        finally:
            conn.close()

    print(f"[INFO] 从数据库读取记录: {len(db_rows)} 行")

    # 3. 比对，找出错误 textId
    mismatches: List[Dict] = []
    not_in_source = 0

    for row in db_rows:
        db_id = row["id"]
        fid = row["fid"]
        db_text_id = str(row["textId"])  # DB 中可能是整型或字符串
        part = int(row["part"])
        source_hash = row["sourceTextHash"]

        key = (fid, part, source_hash)
        correct_text_id = source_index.get(key)
        if correct_text_id is None:
            not_in_source += 1
            continue

        if db_text_id != correct_text_id:
            mismatches.append(
                {
                    "id": db_id,
                    "fid": fid,
                    "wrong_textId": db_text_id,
                    "correct_textId": correct_text_id,
                    "part": part,
                    "sourceTextHash": source_hash,
                }
            )

    print(f"[INFO] 未匹配到源数据的记录: {not_in_source}")
    print(f"[INFO] 发现错误 textId: {len(mismatches)} 条")

    # 4. 输出 CSV
    now_str = datetime.now(timezone.utc).isoformat()
    with csv_path.open("w", encoding="utf-8") as f:
        f.write("id,fid,wrong_textId,correct_textId,part,sourceTextHash\n")
        for m in mismatches:
            fid_escaped = m["fid"].replace('"', '""')
            wrong_escaped = m["wrong_textId"].replace('"', '""')
            correct_escaped = m["correct_textId"].replace('"', '""')
            hash_escaped = m["sourceTextHash"].replace('"', '""')
            f.write(
                f'{m["id"]},"{fid_escaped}","{wrong_escaped}","{correct_escaped}",'
                f'{m["part"]},"{hash_escaped}"\n'
            )
    print(f"[FILE] CSV: {csv_path}")

    # 5. 输出 UPDATE SQL（按主键更新，精准可靠）
    with sql_path.open("w", encoding="utf-8") as f:
        f.write(f"-- Auto-generated by generate_textid_fix_map.py\n")
        f.write(f"-- generated_at_utc: {now_str}\n")
        f.write(f"-- total_mismatches: {len(mismatches)}\n")
        f.write(f"-- source_sqlite: {config['sqlitePath']}\n\n")
        f.write("-- 执行前请确认 text_main.textId 已完成 BIGINT→VARCHAR 列类型迁移\n\n")
        for m in mismatches:
            correct_lit = _escape_sql_string(m["correct_textId"])
            f.write(
                f"UPDATE `{db_table}` SET `textId` = {correct_lit} "
                f"WHERE `id` = {m['id']};\n"
            )
    print(f"[FILE] SQL:  {sql_path}")

    print("[DONE] 修复映射生成完成")
    print(f"[STAT] total_db_rows={len(db_rows)}")
    print(f"[STAT] not_in_source={not_in_source}")
    print(f"[STAT] mismatches={len(mismatches)}")


if __name__ == "__main__":
    main()
    # 用法示例（直接连接，无 SSH 隧道）:
    # python tools/fix_textid/generate_textid_fix_map.py --config tools/fix_textid/generate_textid_fix_map.yaml
    #
    # 用法示例（经 SSH 隧道）:
    # python tools/fix_textid/generate_textid_fix_map.py --config tools/fix_textid/generate_textid_fix_map.yaml --use-ssh-tunnel
