#!/usr/bin/env python3
# 一键执行 Step5/Step6/Step7（无 psql 依赖，自动建立 SSH 隧道）。

import argparse
import os
from pathlib import Path
from typing import Dict

from psycopg import connect

from common import (
    load_env_file,
    require_table_ref,
    start_ssh_tunnel_from_env,
)


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _render_sql(sql_text: str, variables: Dict[str, str]) -> str:
    kept_lines = []
    for line in sql_text.splitlines():
        if line.lstrip().startswith("\\"):
            continue
        kept_lines.append(line)

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
    cursor.execute(rendered_sql, prepare=False)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="执行 Step5/Step6/Step7（Python 版）")
    parser.add_argument("--backup-table", required=True, help="Step5/Step6 使用的备份表")
    parser.add_argument("--next-table", required=True, help="Step5/Step6 使用的新表")
    parser.add_argument("--map-table", required=True, help="Step6 创建、Step7 使用的映射表")
    parser.add_argument("--changes-table", required=True, help="Step7 使用的变更表")
    parser.add_argument("--env", help="环境文件路径（可选）")
    parser.add_argument(
        "--start-step",
        required=True,
        choices=("5", "6", "7"),
        help="从哪个步骤开始执行（5=全部，6=仅 Step6+Step7，7=仅 Step7）",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    start_step = int(args.start_step)

    require_table_ref(args.backup_table, "backup_table")
    require_table_ref(args.next_table, "next_table")
    require_table_ref(args.map_table, "map_table")
    require_table_ref(args.changes_table, "changes_table")

    if args.env:
        os.environ["LOTRO_ENV_PATH"] = str(Path(args.env).expanduser().resolve())

    load_env_file()
    if "LOTRO_DATABASE_DSN" not in os.environ:
        raise RuntimeError("环境变量未设置: LOTRO_DATABASE_DSN")
    dsn = os.environ["LOTRO_DATABASE_DSN"]

    root = Path(__file__).resolve().parents[2]
    step5_sql = root / "tools" / "version_iteration_tool" / "step5_compare_and_inherit.sql"
    step6_sql = root / "tools" / "version_iteration_tool" / "step6_create_text_id_map.sql"
    step7_sql = root / "tools" / "version_iteration_tool" / "step7_migrate_text_changes.sql"

    with start_ssh_tunnel_from_env():
        with connect(dsn) as conn:
            conn.autocommit = True
            with conn.cursor() as cursor:
                if start_step <= 5:
                    print("[INFO] 执行 Step5: compare + inherit")
                    _run_sql_file(
                        cursor,
                        step5_sql,
                        {
                            "backup_table": args.backup_table,
                            "next_table": args.next_table,
                        },
                    )

                if start_step <= 6:
                    print("[INFO] 执行 Step6: create text id map")
                    _run_sql_file(
                        cursor,
                        step6_sql,
                        {
                            "backup_table": args.backup_table,
                            "next_table": args.next_table,
                            "map_table": args.map_table,
                        },
                    )

                if start_step <= 7:
                    print("[INFO] 执行 Step7: migrate text_changes")
                    _run_sql_file(
                        cursor,
                        step7_sql,
                        {
                            "map_table": args.map_table,
                            "changes_table": args.changes_table,
                        },
                    )

    print("[DONE] Step5/Step6/Step7 全部执行完成")


if __name__ == "__main__":
    main()

# python tools/version_iteration_tool/run_step5_to_step7.py \
#     --backup-table lotro.text_main_bak_u46 \
#     --next-table lotro.text_main_next \
#     --map-table lotro.textIdMap_u46_to_u46_1 \
#     --changes-table lotro.text_changes \
#     --start-step 5 \
#     --env .env