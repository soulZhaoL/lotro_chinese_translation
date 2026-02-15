# 版本迭代工具（U46 -> U46.x）

本目录用于执行 `docs/db_version_iteration_runbook.md` 的核心流程。

主流程（每次版本升级都执行）：

1. `step1_backup_text_main.py`：备份主表（rename）
2. `step3_create_text_main_next.py`：创建 `text_main_next`
3. `step4_generate_text_main_next_insert.py`：从 `Texts.db` 生成导入 SQL
4. `step5_compare_and_inherit.sql`：比对备份表与 next 表，分类并继承译文
5. `step6_create_text_id_map.sql`：生成新老 ID 映射（供 `text_changes` 迁移）
6. `step7_migrate_text_changes.sql`：按映射迁移 `text_changes` 并清理未命中记录

独立工具（一次性/按需执行，不属于每次升级主流程）：

- `step2_fill_source_text_hash.py`：回填历史数据的 `sourceTextHash`

所有 Python 脚本都要求 `--config`，不使用硬编码默认配置。

环境变量加载规则（与后端一致）：

- 若设置 `LOTRO_ENV_PATH`，脚本会加载该路径下的环境文件
- 若未设置 `LOTRO_ENV_PATH`，脚本会尝试加载项目根目录 `.env`
- 加载后仍缺少 `database.dsnEnv` 指向的变量时，脚本会直接报错终止

DB 连接规则（与 `server/start_dev.sh` 一致）：

- Step1/Step2/Step3 会自动建立 SSH 隧道后再连库
- 隧道参数来自环境变量：`LOTRO_SSH_HOST`、`LOTRO_SSH_USER`、`LOTRO_SSH_PORT`、`LOTRO_TUNNEL_PORT`、`LOTRO_REMOTE_DB_HOST`、`LOTRO_REMOTE_DB_PORT`
- 若 `LOTRO_TUNNEL_PORT` 已被监听，则复用现有隧道，不重复创建
- Step5/Step6/Step7 的 `psql` 命令不会自动建隧道，执行前需先手动保持隧道可用

## Step1 备份主表

```bash
python tools/version_iteration_tool/step1_backup_text_main.py \
  --config tools/version_iteration_tool/step1_backup_text_main.yaml
```

- 示例：`text_main` -> `text_main_bak_u46`
- 若备份表已存在会直接报错终止

## Step2 创建 text_main_next

```bash
python tools/version_iteration_tool/step3_create_text_main_next.py \
  --config tools/version_iteration_tool/step3_create_text_main_next.yaml
```

- 从备份表 `LIKE ... INCLUDING ALL` 创建 `text_main_next`
- 增加唯一约束 `(fid, textId, part)`
- 强制设置 `id` 自增默认值（`createNext.autoIncrement` 配置的 sequence）
- 前置约束：骨干表（原表/备份表）默认已具备 `sourceTextHash`

## Step3 生成导入 SQL

```bash
python tools/version_iteration_tool/step4_generate_text_main_next_insert.py \
  --config tools/version_iteration_tool/step4_generate_text_main_next_insert.yaml
```

- 输入源：`work_text/Texts.db` 的 `patch_data`
- 分段规则：严格对齐 `tools/valid_format/xlsx_format_check.py`
- 默认建议 `idPattern=\d{2,10}`（最新规则）
- 测试场景可临时改为 `idPattern=\d{4,10}`
- `sourceText` 仅保存 `[]` 内文本
- `part` 在每个 `fid` 内从 1 递增
- `sourceTextHash = sha256(sourceText)`
- 输出示例：`work_text/tmp_text_main_next_insert.sql`

导入命令：

```bash
psql "$LOTRO_DATABASE_DSN" -f work_text/tmp_text_main_next_insert.sql
```

## Step4 比对 + 继承译文（Runbook Step5）

```bash
psql "$LOTRO_DATABASE_DSN" \
  -v backup_table=text_main_bak_u46 \
  -v next_table=text_main_next \
  -f tools/version_iteration_tool/step5_compare_and_inherit.sql
```

该脚本会按 `fid + textId + part` 分类：

- 新增：仅设置 `status=1`，保留 next 表已有 `translatedText/editCount`
- 修改：仅设置 `status=2`，保留 next 表已有 `translatedText/editCount`
- 未变化：用备份表覆盖 `translatedText/status/editCount`

## Step5 生成新老 ID 映射（Runbook Step6）

```bash
psql "$LOTRO_DATABASE_DSN" \
  -v backup_table=text_main_bak_u46 \
  -v next_table=text_main_next \
  -v map_table=textIdMap_u46_to_u46_1 \
  -f tools/version_iteration_tool/step6_create_text_id_map.sql
```

- 仅为“哈希相同”的稳定文本建立映射
- 映射表字段：`oldId/newId/fid/textId/part/sourceTextHash`
- 可直接作为后续 `text_changes` 迁移输入

## Step6 迁移 text_changes（Runbook Step7）

```bash
psql "$LOTRO_DATABASE_DSN" \
  -v map_table=textIdMap_u46_to_u46_1 \
  -v changes_table=text_changes \
  -f tools/version_iteration_tool/step7_migrate_text_changes.sql
```

该脚本会执行：

- 将 `text_changes.textId = map.oldId` 的记录迁移为 `map.newId`
- 清理所有无法映射到 `map.newId` 的记录
- 内置行数一致性断言，防止静默脏迁移

## 一键执行 Step5~Step7（推荐）

为减少 `psql` 参数输入，提供包装脚本：

```bash
./tools/version_iteration_tool/run_step5_to_step7.sh \
  --backup-table lotro.text_main_bak_u46 \
  --next-table lotro.text_main_next \
  --map-table lotro.textIdMap_u46_to_u46_1 \
  --changes-table lotro.text_changes \
  --start-step 5 \
  --env .env
```

- 脚本会自动建立（或复用）SSH 隧道，再按顺序执行 Step5/Step6/Step7
- 所有表名参数必须显式传入，不使用脚本内默认值
- 如未传 `--env`，则依赖当前 shell 已存在所需环境变量
- 若本机没有 `psql` 客户端，脚本会自动切换到 Python 执行器（`run_step5_to_step7.py`）
- `--start-step` 必填：`5`=执行 5/6/7，`6`=只执行 6/7，`7`=只执行 7（用于 Step6 已完成后的重试）

## 独立工具：历史 hash 回填（一次性）

仅当历史表在早期未维护 `sourceTextHash` 时使用；若升级前数据已带 hash，可跳过。

```bash
python tools/version_iteration_tool/step2_fill_source_text_hash.py \
  --config tools/version_iteration_tool/step2_fill_source_text_hash.yaml
```

- 可按配置对指定表批量回填
- 当前示例策略为 `nullOnly`，只更新哈希为空的记录
