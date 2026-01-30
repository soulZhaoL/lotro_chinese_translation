# 任务清单: 文档/Mock/布局/测试与联通方案

目录: `helloagents/plan/202601302309_docs_mock_layout/`

---

## 1. 文档输出
- [√] 1.1 新增 `docs/backend.md`，包含依赖安装、配置说明、启动方式与 OpenAPI 访问，验证 why.md#需求-使用说明文档-场景-新同事本地启动
- [√] 1.2 新增 `docs/frontend.md`，包含依赖安装、Mock 使用、启动方式与联通说明，验证 why.md#需求-使用说明文档-场景-新同事本地启动
- [√] 1.3 新增 `docs/mvp.md`，提供前后端联通步骤与验收清单，验证 why.md#需求-联通方案-场景-前后端联通

## 2. 后端接口注释与文档
- [√] 2.1 为 `server/routes/*.py` 补充接口注释（路由说明/入参/响应），验证 why.md#需求-后端接口注释与-api-文档-场景-快速理解接口
- [√] 2.2 更新 `helloagents/wiki/api.md` 补充响应结构与错误码说明，验证 why.md#需求-后端接口注释与-api-文档-场景-快速理解接口

## 3. 前端 Mock
- [√] 3.1 集成 vite-plugin-mock（`web/vite.config.ts` + `web/mock/*.ts`），验证 why.md#需求-前端-mock-场景-前端独立开发
- [√] 3.2 增加 Mock 开关说明与示例，验证 why.md#需求-前端-mock-场景-前端独立开发

## 4. 页面布局调整
- [√] 4.1 调整 `web/src/App.tsx` 为顶部导航 + 左侧二级菜单，验证 why.md#需求-页面布局-场景-页面导航

## 5. 后端单元测试
- [√] 5.1 增加 `tests/tmp_test_validate.py` 覆盖校验接口基础规则，验证 why.md#需求-后端测试-场景-小范围自测
- [√] 5.2 完善现有测试说明与运行步骤，验证 why.md#需求-后端测试-场景-小范围自测

## 6. 文档与变更同步
- [√] 6.1 更新 `helloagents/CHANGELOG.md`
- [√] 6.2 更新 `helloagents/project.md`（如涉及新的依赖/配置项）

---

## 任务状态符号
- `[ ]` 待执行
- `[√]` 已完成
- `[X]` 执行失败
- `[-]` 已跳过
- `[?]` 待确认
