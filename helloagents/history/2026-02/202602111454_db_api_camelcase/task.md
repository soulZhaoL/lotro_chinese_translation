# 任务清单: 数据库/API 字段统一 camelCase

目录: `helloagents/history/2026-02/202602111454_db_api_camelcase/`

---

## 1. 数据库迁移与后端 SQL
- [√] 1.1 改造 `server/migrations/001_init.sql`，将核心业务列统一为 camelCase。
- [√] 1.2 新增 `server/migrations/002_camel_case_columns.sql`，支持存量库列重命名。
- [√] 1.3 改造 `server/routes/texts.py`、`server/routes/changes.py`、`server/routes/claims.py`、`server/routes/locks.py`、`server/routes/dictionary.py`、`server/routes/validate.py` 的查询与写入字段。
- [√] 1.4 改造 `server/services/auth.py`、`server/routes/deps.py`、`server/hash_password.py`，统一登录用户字段为 `isGuest`、用户主键字段为 `userId`。

## 2. 前端与 Mock 契约同步
- [√] 2.1 改造 `web/src/modules/texts/pages/*`、`web/src/modules/dictionary/pages/Dictionary.tsx`、`web/src/modules/auth/pages/Login.tsx`、`web/src/pages/Translate.tsx` 字段与请求参数。
- [√] 2.2 改造 `web/mock/*`，统一 mock 查询参数、响应字段与请求体字段。

## 3. 测试与工具同步
- [√] 3.1 改造 `tests/tmp_pytest_plugin.py` 与全部 `tests/tmp_test_*.py`，统一为 camelCase 字段。
- [√] 3.2 更新 `tools/valid_format/xlsx_to_insert.yaml` 输出列映射为 camelCase。

## 4. 文档与知识库同步
- [√] 4.1 更新 `helloagents/wiki/api.md`、`helloagents/wiki/data.md`、`helloagents/project.md`。
- [√] 4.2 更新 `docs/backend.md`、`docs/TODO_list.md`、`docs/db_version_iteration_runbook.md`。
- [√] 4.3 更新 `helloagents/CHANGELOG.md` 与 `helloagents/history/index.md` 记录本次改造。

## 5. 验证
- [√] 5.1 执行 `python -m py_compile` 校验后端与测试脚本语法。
- [√] 5.2 执行 `cd web && npx tsc -b --pretty false` 校验前端类型。
- [X] 5.3 执行 `PYTHONPATH=. pytest -q` 进行回归测试。
  > 备注: 当前环境数据库 `127.0.0.1:5433` 未启动/不可达，`psycopg.OperationalError: connection refused`。
- [√] 5.4 执行 `PYTHONPATH=. pytest tests/test_maintenance.py -q`，验证非数据库依赖用例。

---

## 任务状态符号
- `[ ]` 待执行
- `[√]` 已完成
- `[X]` 执行失败
- `[-]` 已跳过
- `[?]` 待确认
