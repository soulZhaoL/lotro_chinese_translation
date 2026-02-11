# 版本迭代工具（text_main -> text_main_next）

本目录用于执行 `docs/db_version_iteration_runbook.md` 的关键步骤：

- Step3: 创建 `text_main_next`（并补齐 `sourceTextHash`）
- Step4: 从 `work_text/Texts.db` 解析文本并生成导入 SQL

## 1) Step3: 创建 text_main_next

配置文件：`tools/version_iteration_tool/step3_create_text_main_next.yaml`

执行命令：

```bash
python tools/version_iteration_tool/step3_create_text_main_next.py \
  --config tools/version_iteration_tool/step3_create_text_main_next.yaml
```

说明：

- `sourceTable` 一般为 Step2 生成的备份表（如 `text_main_bak_u46`）
- `existingTablesNeedHash` 用于补齐 `sourceTextHash` 字段（原表/备份表）
- `nextTable` 将按 `LIKE sourceTable INCLUDING ALL` 创建
- 之后会为 `nextTable` 增加 `(fid, textId, part)` 唯一约束

## 2) Step4: 生成 text_main_next 导入 SQL

配置文件：`tools/version_iteration_tool/step4_generate_text_main_next_insert.yaml`

执行命令：

```bash
python tools/version_iteration_tool/step4_generate_text_main_next_insert.py \
  --config tools/version_iteration_tool/step4_generate_text_main_next_insert.yaml
```

说明：

- 正则按 `idPattern=\d{2,10}` 解析 `textId`
- `sourceText` 仅提取 `[]` 内文本
- `part` 在每个 `fid` 内从 1 递增
- `sourceTextHash` 计算方式：`sha256(sourceText)`（十六进制）
- 结果输出到 `output.sqlPath`（默认示例是 `work_text/tmp_text_main_next_insert.sql`）

## 3) 导入 SQL

生成 SQL 后可执行：

```bash
psql "$LOTRO_DATABASE_DSN" -f work_text/tmp_text_main_next_insert.sql
```

> 建议先在测试库验证行数与 `part` 连续性，再在维护窗口执行正式切换。
