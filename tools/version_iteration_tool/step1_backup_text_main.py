# 文本版本迭代 Step1: 备份 text_main 主表。

import argparse
import os
from pathlib import Path
from typing import Any, Dict

from psycopg import connect
from psycopg.rows import dict_row

from common import (
    ConfigError,
    load_env_file,
    load_yaml_config,
    quote_ident,
    quote_table_ref,
    require_identifier,
    require_key,
    require_table_ref,
    require_type,
    split_table_ref,
    start_ssh_tunnel_from_env,
    table_exists,
)


def _validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    database = require_type(require_key(config, "database", ""), dict, "database")
    backup = require_type(require_key(config, "backup", ""), dict, "backup")

    dsn_env = require_type(require_key(database, "dsnEnv", "database."), str, "database.dsnEnv")
    source_table = require_type(require_key(backup, "sourceTable", "backup."), str, "backup.sourceTable")
    backup_table = require_type(require_key(backup, "backupTable", "backup."), str, "backup.backupTable")
    mode = require_type(require_key(backup, "mode", "backup."), str, "backup.mode")

    if mode != "rename":
        raise ConfigError("backup.mode 仅支持 rename")

    require_table_ref(source_table, "backup.sourceTable")
    require_table_ref(backup_table, "backup.backupTable")

    source_schema, source_name = split_table_ref(source_table)
    backup_schema, backup_name = split_table_ref(backup_table)

    if source_schema != backup_schema:
        raise ConfigError("rename 模式要求 sourceTable 与 backupTable 在同一 schema")
    require_identifier(source_name, "backup.sourceTable.name")
    require_identifier(backup_name, "backup.backupTable.name")

    return {
        "dsnEnv": dsn_env,
        "sourceTable": source_table,
        "backupTable": backup_table,
        "backupName": backup_name,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Step1 备份 text_main")
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
                if table_exists(cursor, config["backupTable"]):
                    raise RuntimeError(f"备份表已存在: {config['backupTable']}")

                cursor.execute(
                    f"ALTER TABLE {quote_table_ref(config['sourceTable'])} "
                    f"RENAME TO {quote_ident(config['backupName'])}"
                )
            conn.commit()

    print("[DONE] Step1 备份完成")
    print(f"[SOURCE] {config['sourceTable']}")
    print(f"[BACKUP] {config['backupTable']}")


if __name__ == "__main__":
    main()

    # python ./tools/version_iteration_tool/step1_backup_text_main.py --config ./tools/version_iteration_tool/step1_backup_text_main.yaml