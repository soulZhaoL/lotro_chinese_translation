# 技术设计: 数据库/API 字段统一 camelCase

## 技术方案

### 核心技术
- PostgreSQL 列重命名（ALTER TABLE ... RENAME COLUMN）
- FastAPI + Pydantic 请求/响应模型同步改造
- React + TypeScript 类型与请求参数同步改造

### 实现要点
- 初始化脚本 `001_init.sql` 直接使用 camelCase 列名（双引号标识）。
- 新增 `002_camel_case_columns.sql`，通过 `information_schema.columns` 条件判断实现幂等重命名。
- 后端所有 SQL 显式引用 camelCase 列并在返回时使用 camelCase 字段。
- 前端查询参数统一为 camelCase（如 `textId/pageSize/sourceKeyword`）。
- Mock 与测试用例同步改为 camelCase，确保本地调试契约一致。

## API 设计
- 文本查询: `textId/sourceText/translatedText/editCount/claimId/claimedBy/claimedAt/isClaimed/pageSize`
- 词典: `termKey/termValue/isActive/pageSize`
- 变更历史: `textId/userId/beforeText/afterText/changedAt`
- 锁定: `lockId/expiresAt/releasedAt`
- 认领: `claimId`
- 登录用户: `isGuest`

## 数据模型
- 所有核心业务列改为 camelCase（见 `server/migrations/001_init.sql` 与 `server/migrations/002_camel_case_columns.sql`）。

## 安全与性能
- 本次为命名与契约统一，不改变权限边界与业务逻辑。
- 保留既有索引与查询结构，仅替换列名引用。

## 测试与验证
- `python -m py_compile` 全量校验后端与测试脚本语法。
- `cd web && npx tsc -b --pretty false` 校验前端 TypeScript。
- `PYTHONPATH=. pytest -q` 尝试回归，受本地数据库未启动影响未通过（连接 127.0.0.1:5433 被拒绝）。
- `PYTHONPATH=. pytest tests/test_maintenance.py -q` 通过（2 passed）。
