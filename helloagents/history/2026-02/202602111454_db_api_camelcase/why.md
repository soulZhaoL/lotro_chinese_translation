# 变更提案: 数据库/API 字段统一 camelCase

## 需求背景
当前数据库列名与后端/前端接口中大量使用 snake_case，命名风格混杂，导致联调时需要频繁做字段映射，增加认知负担与维护成本。

## 变更内容
1. 将核心业务表字段统一为 camelCase（含初始化脚本与存量迁移脚本）。
2. 后端 SQL 查询、请求模型、响应字段、查询参数统一为 camelCase。
3. 前端页面类型定义、请求参数、渲染字段与 Mock 数据统一为 camelCase。
4. 同步更新测试与知识库文档，避免文档与实现漂移。

## 影响范围
- **模块:** 数据迁移、认证、文本、认领、锁定、词典、校验、前端文本/词典模块、Mock
- **文件:** `server/*`, `web/src/*`, `web/mock/*`, `tests/*`, `helloagents/wiki/*`, `docs/*`
- **API:** `/texts/*`, `/changes`, `/claims`, `/locks`, `/dictionary`, `/validate`, `/auth/login`
- **数据:** users / user_roles / permissions / role_permissions / text_main / text_claims / text_locks / text_changes / dictionary_entries

## 风险评估
- **风险:** 上线后若数据库未执行迁移脚本，接口会直接报 SQL 列不存在。
- **缓解:** 提供 `server/migrations/002_camel_case_columns.sql` 做存量库列重命名；文档明确升级顺序。
