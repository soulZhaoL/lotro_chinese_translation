# 任务清单: 文本模板下载/上传

目录: `helloagents/history/2026-03/202603011352_text_import_export_template/`

---

## 1. 后端下载/上传接口
- [√] 1.1 在 `server/routes/texts.py` 新增下载接口，按固定模板导出 xlsx。
- [√] 1.2 在 `server/routes/texts.py` 新增上传接口，解析 xlsx 并校验表头和字段类型。
- [√] 1.3 实现“编号定位 + fid/textId/part 强校验 + 原子更新 + 变更记录写入”。
- [√] 1.4 补充上传依赖与配置校验（禁止默认值）。

## 2. 前端入口与上传交互
- [√] 2.1 在 `web/src/modules/texts/pages/TextsList.tsx` 增加下载与上传按钮。
- [√] 2.2 适配上传文件选择与结果提示，上传成功后刷新列表。
- [√] 2.3 调整 `web/src/api.ts` 对 FormData 的请求头处理。

## 3. 测试与验证
- [√] 3.1 新增下载/上传接口测试（成功与失败路径）。
- [-] 3.2 执行文本相关 pytest 用例并确认通过。
> 备注: 已完成纯逻辑测试（`tests/tmp_test_text_template_validation.py`，6 passed）；数据库集成测试默认按新策略跳过，需在 SSH 隧道可用时使用 `PYTHONPATH=. pytest --run-db-tests -q tests/tmp_test_text_template_io.py tests/tmp_test_translate.py tests/tmp_test_texts_nested.py` 执行。

## 4. 知识库同步
- [√] 4.1 更新 `helloagents/wiki/api.md`、`helloagents/wiki/modules/text.md`。
- [√] 4.2 更新 `helloagents/CHANGELOG.md`、`helloagents/history/index.md`。
- [√] 4.3 将方案包迁移至 `helloagents/history/2026-03/` 并更新任务状态。

---

## 任务状态符号
- `[ ]` 待执行
- `[√]` 已完成
- `[X]` 执行失败
- `[-]` 已跳过
- `[?]` 待确认
