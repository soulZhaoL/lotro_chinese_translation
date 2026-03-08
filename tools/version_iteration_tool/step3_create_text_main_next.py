# 文本版本迭代 Step3: 创建 text_main_next。

import argparse
import os
from pathlib import Path
from typing import Any, Dict

from common import (
    column_exists,
    connect_mysql_from_dsn,
    load_env_file,
    load_yaml_config,
    quote_ident,
    quote_table_ref,
    require_identifier,
    require_runtime_env,
    require_key,
    resolve_env_table_ref,
    require_type,
    start_ssh_tunnel_from_env,
    table_exists,
)


def _validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    runtime_env = require_runtime_env(
        require_type(require_key(config, "env", ""), str, "env"),
        "env",
    )
    database = require_type(require_key(config, "database", ""), dict, "database")
    create_cfg = require_type(require_key(config, "createNext", ""), dict, "createNext")

    dsn_env = require_type(require_key(database, "dsnEnv", "database."), str, "database.dsnEnv")
    source_table = resolve_env_table_ref(
        require_type(
            require_key(create_cfg, "sourceTable", "createNext."),
            str,
            "createNext.sourceTable",
        ),
        runtime_env,
        "createNext.sourceTable",
    )
    next_table = resolve_env_table_ref(
        require_type(
            require_key(create_cfg, "nextTable", "createNext."),
            str,
            "createNext.nextTable",
        ),
        runtime_env,
        "createNext.nextTable",
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

    require_identifier(id_column, "createNext.autoIncrement.idColumn")

    return {
        "env": runtime_env,
        "dsnEnv": dsn_env,
        "sourceTable": source_table,
        "nextTable": next_table,
        "idColumn": id_column,
    }


def _ensure_auto_increment(cursor, table_ref: str, id_column: str) -> None:
    if not column_exists(cursor, table_ref, id_column):
        raise RuntimeError(f"自增列不存在: {table_ref}.{id_column}")

    cursor.execute(
        f"ALTER TABLE {quote_table_ref(table_ref)} "
        f"MODIFY COLUMN {quote_ident(id_column)} BIGINT NOT NULL AUTO_INCREMENT"
    )
    print(f"[OK] 已设置自增: {table_ref}.{id_column}")


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
        with connect_mysql_from_dsn(dsn) as conn:
            with conn.cursor() as cursor:
                if not table_exists(cursor, config["sourceTable"]):
                    raise RuntimeError(f"源表不存在: {config['sourceTable']}")
                if table_exists(cursor, config["nextTable"]):
                    raise RuntimeError(f"目标表已存在，请先手动处理: {config['nextTable']}")

                cursor.execute(
                    f"CREATE TABLE {quote_table_ref(config['nextTable'])} "
                    f"LIKE {quote_table_ref(config['sourceTable'])}"
                )
                print(f"[OK] [{config['env']}] 已创建新表: {config['nextTable']}")

                _ensure_auto_increment(
                    cursor,
                    config["nextTable"],
                    config["idColumn"],
                )

            conn.commit()

    print("[DONE] Step3 完成")


if __name__ == "__main__":
    main()
    # python ./tools/version_iteration_tool/step3_create_text_main_next.py --config ./tools/version_iteration_tool/step3_create_text_main_next.yaml 
