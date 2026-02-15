# 文本版本迭代 Step2: 计算并回填 sourceTextHash。

import argparse
import hashlib
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

from psycopg import connect
from psycopg.rows import dict_row

from common import (
    ConfigError,
    column_exists,
    load_env_file,
    load_yaml_config,
    quote_ident,
    quote_table_ref,
    require_identifier,
    require_key,
    require_table_ref,
    require_type,
    start_ssh_tunnel_from_env,
    table_exists,
)


def _validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    database = require_type(require_key(config, "database", ""), dict, "database")
    hash_cfg = require_type(require_key(config, "hash", ""), dict, "hash")

    dsn_env = require_type(require_key(database, "dsnEnv", "database."), str, "database.dsnEnv")
    tables = require_type(require_key(hash_cfg, "tables", "hash."), list, "hash.tables")
    id_column = require_type(require_key(hash_cfg, "idColumn", "hash."), str, "hash.idColumn")
    source_text_column = require_type(
        require_key(hash_cfg, "sourceTextColumn", "hash."), str, "hash.sourceTextColumn"
    )
    hash_column = require_type(require_key(hash_cfg, "hashColumn", "hash."), str, "hash.hashColumn")
    batch_size = require_type(require_key(hash_cfg, "batchSize", "hash."), int, "hash.batchSize")
    update_policy = require_type(require_key(hash_cfg, "updatePolicy", "hash."), str, "hash.updatePolicy")
    null_source_policy = require_type(
        require_key(hash_cfg, "nullSourcePolicy", "hash."), str, "hash.nullSourcePolicy"
    )
    missing_table_policy = require_type(
        require_key(hash_cfg, "missingTablePolicy", "hash."), str, "hash.missingTablePolicy"
    )

    if not tables:
        raise ConfigError("hash.tables 不能为空")
    normalized_tables: List[str] = []
    for idx, table_ref in enumerate(tables):
        table_value = require_type(table_ref, str, f"hash.tables[{idx}]")
        normalized_tables.append(require_table_ref(table_value, f"hash.tables[{idx}]"))

    require_identifier(id_column, "hash.idColumn")
    require_identifier(source_text_column, "hash.sourceTextColumn")
    require_identifier(hash_column, "hash.hashColumn")

    if batch_size <= 0:
        raise ConfigError("hash.batchSize 必须大于 0")
    if update_policy not in ("nullOnly", "all"):
        raise ConfigError("hash.updatePolicy 仅支持 nullOnly/all")
    if null_source_policy not in ("emptyString", "error"):
        raise ConfigError("hash.nullSourcePolicy 仅支持 emptyString/error")
    if missing_table_policy not in ("skip", "error"):
        raise ConfigError("hash.missingTablePolicy 仅支持 skip/error")

    return {
        "dsnEnv": dsn_env,
        "tables": normalized_tables,
        "idColumn": id_column,
        "sourceTextColumn": source_text_column,
        "hashColumn": hash_column,
        "batchSize": batch_size,
        "updatePolicy": update_policy,
        "nullSourcePolicy": null_source_policy,
        "missingTablePolicy": missing_table_policy,
    }


def _build_hash_text(source_text: Any, null_source_policy: str, table_ref: str, row_id: Any) -> str:
    if source_text is None:
        if null_source_policy == "error":
            raise RuntimeError(f"sourceText 为空且策略为 error: table={table_ref}, id={row_id}")
        return ""
    return str(source_text)


def _fill_table_hash(cursor, config: Dict[str, Any], table_ref: str) -> Tuple[int, int]:
    id_column = config["idColumn"]
    source_text_column = config["sourceTextColumn"]
    hash_column = config["hashColumn"]

    if not table_exists(cursor, table_ref):
        if config["missingTablePolicy"] == "skip":
            print(f"[SKIP] 表不存在，跳过: {table_ref}")
            return 0, 0
        raise RuntimeError(f"表不存在: {table_ref}")

    for column_name in (id_column, source_text_column, hash_column):
        if not column_exists(cursor, table_ref, column_name):
            raise RuntimeError(f"列不存在: {table_ref}.{column_name}")

    where_clause = ""
    if config["updatePolicy"] == "nullOnly":
        where_clause = f"WHERE {quote_ident(hash_column)} IS NULL"

    select_sql = (
        f"SELECT {quote_ident(id_column)} AS row_id, {quote_ident(source_text_column)} AS source_text "
        f"FROM {quote_table_ref(table_ref)} {where_clause} ORDER BY {quote_ident(id_column)}"
    )

    total_scanned = 0
    total_updated = 0
    batch: List[Tuple[str, Any]] = []

    cursor.execute(select_sql)
    while True:
        rows = cursor.fetchmany(config["batchSize"])
        if not rows:
            break
        total_scanned += len(rows)

        for row in rows:
            source_text = _build_hash_text(row["source_text"], config["nullSourcePolicy"], table_ref, row["row_id"])
            source_hash = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
            batch.append((source_hash, row["row_id"]))

        cursor.executemany(
            f"UPDATE {quote_table_ref(table_ref)} "
            f"SET {quote_ident(hash_column)} = %s WHERE {quote_ident(id_column)} = %s",
            batch,
        )
        total_updated += len(batch)
        batch = []

    return total_scanned, total_updated


def main() -> None:
    parser = argparse.ArgumentParser(description="Step2 回填 sourceTextHash")
    parser.add_argument("--config", required=True, help="配置文件路径")
    args = parser.parse_args()

    config = _validate_config(load_yaml_config(Path(args.config).expanduser().resolve()))
    load_env_file()
    dsn_env = config["dsnEnv"]
    if dsn_env not in os.environ:
        raise RuntimeError(f"环境变量未设置: {dsn_env}")

    dsn = os.environ[dsn_env]

    with start_ssh_tunnel_from_env():
        with connect(dsn, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                for table_ref in config["tables"]:
                    scanned, updated = _fill_table_hash(cursor, config, table_ref)
                    conn.commit()
                    print(f"[DONE] {table_ref} scanned={scanned}, updated={updated}")

    print("[DONE] Step2 完成")


if __name__ == "__main__":
    main()
