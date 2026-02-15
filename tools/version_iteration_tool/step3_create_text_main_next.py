# 文本版本迭代 Step3: 创建 text_main_next。

import argparse
import os
from pathlib import Path
from typing import Any, Dict, List

from psycopg import connect
from psycopg.rows import dict_row

from common import (
    ConfigError,
    column_exists,
    constraint_exists,
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
    create_cfg = require_type(require_key(config, "createNext", ""), dict, "createNext")

    dsn_env = require_type(require_key(database, "dsnEnv", "database."), str, "database.dsnEnv")
    source_table = require_type(
        require_key(create_cfg, "sourceTable", "createNext."),
        str,
        "createNext.sourceTable",
    )
    next_table = require_type(
        require_key(create_cfg, "nextTable", "createNext."),
        str,
        "createNext.nextTable",
    )
    unique_constraint_name = require_type(
        require_key(create_cfg, "uniqueConstraintName", "createNext."),
        str,
        "createNext.uniqueConstraintName",
    )
    unique_columns = require_type(
        require_key(create_cfg, "uniqueColumns", "createNext."),
        list,
        "createNext.uniqueColumns",
    )
    auto_inc_cfg = require_type(
        require_key(create_cfg, "autoIncrement", "createNext."),
        dict,
        "createNext.autoIncrement",
    )
    id_column = require_type(
        require_key(auto_inc_cfg, "idColumn", "createNext.autoIncrement."),
        str,
        "createNext.autoIncrement.idColumn",
    )
    sequence_name = require_type(
        require_key(auto_inc_cfg, "sequenceName", "createNext.autoIncrement."),
        str,
        "createNext.autoIncrement.sequenceName",
    )

    require_table_ref(source_table, "createNext.sourceTable")
    require_table_ref(next_table, "createNext.nextTable")
    require_identifier(unique_constraint_name, "createNext.uniqueConstraintName")
    require_identifier(id_column, "createNext.autoIncrement.idColumn")
    require_table_ref(sequence_name, "createNext.autoIncrement.sequenceName")

    if not unique_columns:
        raise ConfigError("createNext.uniqueColumns 不能为空")
    normalized_unique_columns: List[str] = []
    for idx, column_name in enumerate(unique_columns):
        value = require_type(column_name, str, f"createNext.uniqueColumns[{idx}]")
        normalized_unique_columns.append(require_identifier(value, f"createNext.uniqueColumns[{idx}]"))

    return {
        "dsnEnv": dsn_env,
        "sourceTable": source_table,
        "nextTable": next_table,
        "uniqueConstraintName": unique_constraint_name,
        "uniqueColumns": normalized_unique_columns,
        "idColumn": id_column,
        "sequenceName": sequence_name,
    }


def _add_unique_constraint(cursor, table_ref: str, constraint_name: str, columns: List[str]) -> None:
    if constraint_exists(cursor, table_ref, constraint_name):
        raise RuntimeError(f"唯一约束已存在: {table_ref}.{constraint_name}")
    columns_sql = ", ".join(quote_ident(column_name) for column_name in columns)
    cursor.execute(
        f"ALTER TABLE {quote_table_ref(table_ref)} "
        f"ADD CONSTRAINT {quote_ident(constraint_name)} UNIQUE ({columns_sql})"
    )
    print(f"[OK] 已创建唯一约束: {table_ref}.{constraint_name}")


def _ensure_auto_increment(cursor, table_ref: str, id_column: str, sequence_name: str) -> None:
    if not column_exists(cursor, table_ref, id_column):
        raise RuntimeError(f"自增列不存在: {table_ref}.{id_column}")

    cursor.execute(f"CREATE SEQUENCE IF NOT EXISTS {quote_table_ref(sequence_name)}")
    cursor.execute(
        f"ALTER SEQUENCE {quote_table_ref(sequence_name)} "
        f"OWNED BY {quote_table_ref(table_ref)}.{quote_ident(id_column)}"
    )
    regclass_ref = quote_table_ref(sequence_name).replace("'", "''")
    cursor.execute(
        f"ALTER TABLE {quote_table_ref(table_ref)} "
        f"ALTER COLUMN {quote_ident(id_column)} SET DEFAULT nextval('{regclass_ref}'::regclass)"
    )
    print(f"[OK] 已设置自增: {table_ref}.{id_column} -> {sequence_name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Step3 创建 text_main_next")
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
                if not table_exists(cursor, config["sourceTable"]):
                    raise RuntimeError(f"源表不存在: {config['sourceTable']}")
                if table_exists(cursor, config["nextTable"]):
                    raise RuntimeError(f"目标表已存在，请先手动处理: {config['nextTable']}")

                cursor.execute(
                    f"CREATE TABLE {quote_table_ref(config['nextTable'])} "
                    f"(LIKE {quote_table_ref(config['sourceTable'])} INCLUDING ALL)"
                )
                print(f"[OK] 已创建新表: {config['nextTable']}")

                _add_unique_constraint(
                    cursor,
                    config["nextTable"],
                    config["uniqueConstraintName"],
                    config["uniqueColumns"],
                )
                _ensure_auto_increment(
                    cursor,
                    config["nextTable"],
                    config["idColumn"],
                    config["sequenceName"],
                )

            conn.commit()

    print("[DONE] Step3 完成")


if __name__ == "__main__":
    main()
    # python ./tools/version_iteration_tool/step3_create_text_main_next.py --config ./tools/version_iteration_tool/step3_create_text_main_next.yaml 
