# 任务清单: 词典管理菜单升级

目录: `helloagents/plan/202604171725_dictionary_management_upgrade/`

---

## 1. 数据层与后端接口
- [ ] 1.1 在 `server/migrations/` 中新增词典表迁移，补充 `remark`、`lastModifiedBy` 字段与 `termKey` 唯一约束，验证 `why.md#需求-模板导出与导入-场景-导入词典文件`
- [ ] 1.2 在 `server/routes/dictionary.py` 中增强列表查询与新增/修改逻辑，返回 `remark`、`lastModifiedBy`、`lastModifiedByName`，验证 `why.md#需求-列表补充运营信息-场景-查看词典列表`
- [ ] 1.3 在 `server/routes/dictionary.py` 中实现 `GET /dictionary/template`、`GET /dictionary/download`、`POST /dictionary/upload`，验证 `why.md#需求-模板导出与导入-场景-下载模板`

## 2. 前端词典页面改造
- [ ] 2.1 在 `web/src/modules/dictionary/index.tsx` 中将词典页面重构为 `ProTable` 搜索与分页结构，验证 `why.md#需求-词典管理页面风格对齐-场景-进入词典管理页`
- [ ] 2.2 在 `web/src/modules/dictionary/types.ts` 与新增辅助文件中补充列表字段、导入导出与弹窗表单类型，验证 `why.md#需求-单条修改词条-场景-修改已有词条`
- [ ] 2.3 在 `web/src/modules/dictionary/index.tsx` 中补齐新增/修改弹窗、导出、下载模板、导入按钮与反馈状态，验证 `why.md#需求-模板导出与导入-场景-导入词典文件`

## 3. Mock 与测试
- [ ] 3.1 在 `web/mock/dictionary.ts` 与 `web/mock/rules.ts` 中补齐备注、修改人及模板导入导出 mock，验证 `why.md#需求-词典管理页面风格对齐-场景-进入词典管理页`
- [ ] 3.2 在 `tests/` 中补充词典接口测试，覆盖新增、修改、导入新增、导入覆盖、失败回滚场景，验证 `why.md#需求-模板导出与导入-场景-导入词典文件`

## 4. 安全检查
- [ ] 4.1 执行词典导入安全检查（模板校验、事务回滚、重复 key、鉴权与错误提示）

## 5. 文档更新
- [ ] 5.1 更新 `helloagents/wiki/modules/dictionary.md`、`helloagents/wiki/api.md`、`helloagents/wiki/data.md`

## 6. 测试
- [ ] 6.1 运行词典相关 pytest 与前端构建验证，确认列表、修改、导入、导出链路可用

---

## 任务状态符号
- `[ ]` 待执行
- `[√]` 已完成
- `[X]` 执行失败
- `[-]` 已跳过
- `[?]` 待确认
