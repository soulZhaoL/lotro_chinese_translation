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


def _read_sql(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"SQL 文件不存在: {path}")
    return path.read_text(encoding="utf-8")


def _render_block(block: str, variables: Dict[str, str]) -> str:
    """过滤并渲染 // 分隔的单个 SQL 块。"""
    kept_lines = []
    for line in block.splitlines():
        if line.lstrip().startswith("\\"):
            continue
        if line.strip().upper().startswith("DELIMITER"):
            continue
        kept_lines.append(line)
    rendered = "\n".join(kept_lines).strip()
    # 跳过纯注释块（无实质 SQL）
    non_comment = "\n".join(l for l in rendered.splitlines() if not l.strip().startswith("--")).strip()
    if not non_comment:
        return ""
    for name, value in variables.items():
        rendered = rendered.replace(f":'{name}'", _sql_literal(value))
    return rendered


def _run_sql_file(cursor, path: Path, variables: Dict[str, str]) -> None:
    sql_text = _read_sql(path)
    # 按 // 分割为独立语句逐条执行，使任何失败语句能立即精确报错
    for i, block in enumerate(sql_text.split("//"), start=1):
        stmt = _render_block(block, variables)
        if not stmt:
            continue
        try:
            cursor.execute(stmt)
            while cursor.nextset():
                pass
        except Exception as exc:
            preview = stmt[:300].replace("\n", " ")
            raise RuntimeError(f"[SQL块#{i}] {exc}\n  语句: {preview}") from exc


_STEP5_BATCH_SIZE = 10000


def _run_step5(cursor, conn, backup_table: str, next_table: str) -> None:
    """Step5: 比对备份表与 next 表，分类并继承译文。class=3 分批提交，避免超大事务。"""

    def fetch_cnt(sql: str) -> int:
        cursor.execute(sql)
        row = cursor.fetchone()
        return int(row["cnt"])

    # 前置验证
    cnt = fetch_cnt(
        f"SELECT COUNT(*) AS cnt FROM ("
        f"SELECT fid, `textId` FROM {backup_table} "
        f"GROUP BY fid, `textId` HAVING COUNT(*) > 1) t"
    )
    if cnt > 0:
        raise RuntimeError(f"备份表存在重复 key(fid,textId)，数量={cnt}")

    cnt = fetch_cnt(
        f"SELECT COUNT(*) AS cnt FROM ("
        f"SELECT fid, `textId` FROM {next_table} "
        f"GROUP BY fid, `textId` HAVING COUNT(*) > 1) t"
    )
    if cnt > 0:
        raise RuntimeError(f"next表存在重复 key(fid,textId)，数量={cnt}")

    cnt = fetch_cnt(f"SELECT COUNT(*) AS cnt FROM {backup_table} WHERE `sourceTextHash` IS NULL")
    if cnt > 0:
        raise RuntimeError(f"备份表存在空哈希记录，数量={cnt}")

    cnt = fetch_cnt(f"SELECT COUNT(*) AS cnt FROM {next_table} WHERE `sourceTextHash` IS NULL")
    if cnt > 0:
        raise RuntimeError(f"next表存在空哈希记录，数量={cnt}")

    # 创建分类临时表（done 字段用于分批标记）
    cursor.execute("DROP TEMPORARY TABLE IF EXISTS tmp_step5_classify")
    cursor.execute(
        "CREATE TEMPORARY TABLE tmp_step5_classify ("
        "  next_id BIGINT NOT NULL,"
        "  bak_id BIGINT NULL,"
        "  class TINYINT NOT NULL,"
        "  done TINYINT NOT NULL DEFAULT 0,"
        "  PRIMARY KEY (next_id),"
        "  KEY idx_cls_class_done (class, done),"
        "  KEY idx_cls_bak_id (bak_id)"
        ") ENGINE=InnoDB"
    )

    # 填充分类数据（全量一次 INSERT，依赖 (fid,textId,part) 索引加速 JOIN）
    cursor.execute(
        f"INSERT INTO tmp_step5_classify (next_id, bak_id, class) "
        f"SELECT nxt.id, bak.id, "
        f"CASE WHEN bak.id IS NULL THEN 1 "
        f"WHEN nxt.`sourceTextHash` <=> bak.`sourceTextHash` THEN 3 "
        f"ELSE 2 END "
        f"FROM {next_table} AS nxt "
        f"LEFT JOIN {backup_table} AS bak "
        f"ON nxt.fid = bak.fid AND nxt.`textId` = bak.`textId`"
    )

    cursor.execute(
        "SELECT COALESCE(SUM(class=1),0) AS new_cnt, "
        "COALESCE(SUM(class=2),0) AS changed_cnt, "
        "COALESCE(SUM(class=3),0) AS unchanged_cnt "
        "FROM tmp_step5_classify"
    )
    row = cursor.fetchone()
    new_cnt, changed_cnt, unchanged_cnt = int(row["new_cnt"]), int(row["changed_cnt"]), int(row["unchanged_cnt"])
    print(f"[INFO] Step5 分类: 新增={new_cnt} 修改={changed_cnt} 未变={unchanged_cnt}")

    # class=1,2 UPDATE（数量通常较少，一次提交）
    cursor.execute(
        f"UPDATE {next_table} AS nxt "
        f"JOIN tmp_step5_classify AS cls ON cls.next_id = nxt.id "
        f"SET nxt.status = CASE cls.class WHEN 1 THEN 1 WHEN 2 THEN 2 END, "
        f"nxt.`uptTime` = NOW() "
        f"WHERE cls.class IN (1, 2)"
    )
    updated_12 = cursor.rowcount
    conn.commit()
    if updated_12 != new_cnt + changed_cnt:
        raise RuntimeError(
            f"新增+修改更新行数不一致: expected={new_cnt + changed_cnt} actual={updated_12}"
        )
    print(f"[INFO] Step5 class=1,2 完成: {updated_12} 行")

    # class=3 分批 UPDATE（继承译文，数量大，每批单独提交）
    total_updated = 0
    batch = 0
    while True:
        cursor.execute(
            f"SELECT next_id FROM tmp_step5_classify "
            f"WHERE class = 3 AND done = 0 LIMIT {_STEP5_BATCH_SIZE}"
        )
        ids = [r["next_id"] for r in cursor.fetchall()]
        if not ids:
            break
        id_list = ",".join(str(i) for i in ids)

        cursor.execute(
            f"UPDATE {next_table} AS nxt "
            f"JOIN tmp_step5_classify AS cls ON cls.next_id = nxt.id "
            f"JOIN {backup_table} AS bak ON bak.id = cls.bak_id "
            f"SET nxt.`translatedText` = bak.`translatedText`, "
            f"nxt.status = bak.status, "
            f"nxt.`editCount` = bak.`editCount`, "
            f"nxt.`uptTime` = bak.`uptTime` "
            f"WHERE cls.next_id IN ({id_list})"
        )
        affected = cursor.rowcount
        cursor.execute(f"UPDATE tmp_step5_classify SET done = 1 WHERE next_id IN ({id_list})")
        conn.commit()
        total_updated += affected
        batch += 1
        print(f"[INFO] Step5 class=3 批次 {batch}: {affected} 行, 累计 {total_updated}/{unchanged_cnt}")

    if total_updated != unchanged_cnt:
        raise RuntimeError(
            f"继承更新行数不一致: expected={unchanged_cnt} actual={total_updated}"
        )
    cursor.execute("DROP TEMPORARY TABLE IF EXISTS tmp_step5_classify")
    print(f"[INFO] Step5 汇总: 新增={new_cnt} 修改={changed_cnt} 继承={total_updated}")


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
    step6_sql = root / "tools" / "version_iteration_tool" / "step6_create_text_id_map.sql"
    step7_sql = root / "tools" / "version_iteration_tool" / "step7_migrate_text_changes.sql"

    with start_ssh_tunnel_from_env():
        with connect_mysql_from_dsn(dsn) as conn:
            conn.autocommit(False)
            try:
                with conn.cursor() as cursor:
                    print(f"[INFO] 运行环境: {runtime_env}")
                    print(f"[INFO] backup_table: {backup_table}")
                    print(f"[INFO] next_table: {next_table}")
                    print(f"[INFO] map_table: {map_table}")
                    print(f"[INFO] changes_table: {changes_table}")

                    if start_step <= 5:
                        print("[INFO] 执行 Step5: compare + inherit")
                        started = time.monotonic()
                        _run_step5(cursor, conn, backup_table, next_table)
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
            except BaseException:
                conn.rollback()
                raise

    print("[DONE] Step5/Step6/Step7 全部执行完成")


if __name__ == "__main__":
    main()

    # python ./tools/version_iteration_tool/run_step5_to_step7.py --config ./tools/version_iteration_tool/run_step5_to_step7.yaml --env .env
