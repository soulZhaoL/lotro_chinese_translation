#!/usr/bin/env python3
# 一键执行 Step5/Step6/Step7（自动建立 SSH 隧道）。

import argparse
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from common import (
    ConfigError,
    connect_mysql_from_dsn,
    load_env_file,
    load_yaml_config,
    require_key,
    require_runtime_env,
    require_type,
    resolve_env_table_ref,
    start_ssh_tunnel_from_env,
)


def _sql_literal(value: str) -> str:
    text = value
    text = text.replace("\\", "\\\\")
    text = text.replace("\0", "\\0")
    text = text.replace("\b", "\\b")
    text = text.replace("\t", "\\t")
    text = text.replace("\n", "\\n")
    text = text.replace("\f", "\\f")
    text = text.replace("\r", "\\r")
    text = text.replace("\x1a", "\\Z")
    text = text.replace("'", "''")
    return "'" + text + "'"


def _render_sql(sql_text: str, variables: Dict[str, str]) -> str:
    kept_lines = []
    for line in sql_text.splitlines():
        stripped = line.strip()
        if line.lstrip().startswith("\\"):
            continue
        if stripped.upper().startswith("DELIMITER "):
            continue

        normalized = line
        if stripped.endswith("//"):
            marker_index = normalized.rfind("//")
            normalized = normalized[:marker_index].rstrip()
            if not normalized.endswith(";"):
                normalized += ";"
        kept_lines.append(normalized)

    rendered = "\n".join(kept_lines)
    for name, value in variables.items():
        rendered = rendered.replace(f":'{name}'", _sql_literal(value))
    return rendered


def _read_sql(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"SQL 文件不存在: {path}")
    return path.read_text(encoding="utf-8")


def _run_sql_file(cursor, path: Path, variables: Dict[str, str]) -> None:
    sql_text = _read_sql(path)
    rendered_sql = _render_sql(sql_text, variables)
    cursor.execute(rendered_sql)
    while cursor.nextset():
        pass


def _validate_config(config: Dict[str, Any], start_step_override: Optional[int]) -> Dict[str, Any]:
    runtime_env = require_runtime_env(
        require_type(require_key(config, "env", ""), str, "env"),
        "env",
    )
    database = require_type(require_key(config, "database", ""), dict, "database")
    tables = require_type(require_key(config, "tables", ""), dict, "tables")

    dsn_env = require_type(require_key(database, "dsnEnv", "database."), str, "database.dsnEnv")

    backup_table = resolve_env_table_ref(
        require_type(require_key(tables, "backupTable", "tables."), str, "tables.backupTable"),
        runtime_env, "tables.backupTable",
    )
    next_table = resolve_env_table_ref(
        require_type(require_key(tables, "nextTable", "tables."), str, "tables.nextTable"),
        runtime_env, "tables.nextTable",
    )
    map_table = resolve_env_table_ref(
        require_type(require_key(tables, "mapTable", "tables."), str, "tables.mapTable"),
        runtime_env, "tables.mapTable",
    )
    changes_table = resolve_env_table_ref(
        require_type(require_key(tables, "changesTable", "tables."), str, "tables.changesTable"),
        runtime_env, "tables.changesTable",
    )

    if start_step_override is not None:
        start_step = start_step_override
    else:
        start_step_raw = require_type(require_key(config, "startStep", ""), int, "startStep")
        if start_step_raw not in (5, 6, 7):
            raise ConfigError(f"startStep 仅支持 5/6/7，当前值: {start_step_raw}")
        start_step = start_step_raw

    return {
        "env": runtime_env,
        "dsnEnv": dsn_env,
        "backupTable": backup_table,
        "nextTable": next_table,
        "mapTable": map_table,
        "changesTable": changes_table,
        "startStep": start_step,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="执行 Step5/Step6/Step7（Python 版）")
    parser.add_argument("--config", required=True, help="配置文件路径")
    parser.add_argument("--env", help="环境文件路径（可选）")
    parser.add_argument(
        "--start-step",
        choices=("5", "6", "7"),
        help="从哪个步骤开始执行，覆盖配置文件中的 startStep（5=全部，6=仅 Step6+Step7，7=仅 Step7）",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if args.env:
        os.environ["LOTRO_ENV_PATH"] = str(Path(args.env).expanduser().resolve())

    raw_config = load_yaml_config(Path(args.config).expanduser().resolve())
    start_step_override = int(args.start_step) if args.start_step else None
    config = _validate_config(raw_config, start_step_override)

    load_env_file()
    dsn_env = config["dsnEnv"]
    if dsn_env not in os.environ:
        raise RuntimeError(f"环境变量未设置: {dsn_env}")
    dsn = os.environ[dsn_env]

    backup_table = config["backupTable"]
    next_table = config["nextTable"]
    map_table = config["mapTable"]
    changes_table = config["changesTable"]
    start_step = config["startStep"]
    runtime_env = config["env"]

    root = Path(__file__).resolve().parents[2]
    step5_sql = root / "tools" / "version_iteration_tool" / "step5_compare_and_inherit.sql"
    step6_sql = root / "tools" / "version_iteration_tool" / "step6_create_text_id_map.sql"
    step7_sql = root / "tools" / "version_iteration_tool" / "step7_migrate_text_changes.sql"

    with start_ssh_tunnel_from_env():
        with connect_mysql_from_dsn(dsn) as conn:
            conn.autocommit(False)
            with conn.cursor() as cursor:
                print(f"[INFO] 运行环境: {runtime_env}")
                print(f"[INFO] backup_table: {backup_table}")
                print(f"[INFO] next_table: {next_table}")
                print(f"[INFO] map_table: {map_table}")
                print(f"[INFO] changes_table: {changes_table}")

                if start_step <= 5:
                    print("[INFO] 执行 Step5: compare + inherit")
                    started = time.monotonic()
                    _run_sql_file(
                        cursor,
                        step5_sql,
                        {
                            "backup_table": backup_table,
                            "next_table": next_table,
                        },
                    )
                    conn.commit()
                    elapsed = time.monotonic() - started
                    print(f"[INFO] Step5 完成, 耗时 {elapsed:.2f}s")

                if start_step <= 6:
                    print("[INFO] 执行 Step6: create text id map")
                    started = time.monotonic()
                    _run_sql_file(
                        cursor,
                        step6_sql,
                        {
                            "backup_table": backup_table,
                            "next_table": next_table,
                            "map_table": map_table,
                        },
                    )
                    conn.commit()
                    elapsed = time.monotonic() - started
                    print(f"[INFO] Step6 完成, 耗时 {elapsed:.2f}s")

                if start_step <= 7:
                    print("[INFO] 执行 Step7: migrate text_changes")
                    started = time.monotonic()
                    _run_sql_file(
                        cursor,
                        step7_sql,
                        {
                            "map_table": map_table,
                            "changes_table": changes_table,
                        },
                    )
                    conn.commit()
                    elapsed = time.monotonic() - started
                    print(f"[INFO] Step7 完成, 耗时 {elapsed:.2f}s")

    print("[DONE] Step5/Step6/Step7 全部执行完成")


if __name__ == "__main__":
    main()

    # python ./tools/version_iteration_tool/run_step5_to_step7.py --config ./tools/version_iteration_tool/run_step5_to_step7.yaml --env .env
