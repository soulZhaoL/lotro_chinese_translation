# 任务清单: 词典筛选解耦与文本列表/编辑体验优化

目录: `helloagents/plan/202601311805_ui_dict_texts/`

---

## 1. 词典筛选与新增弹窗
- [√] 1.1 在 `server/routes/dictionary.py` 增加 term_key/term_value 查询参数并保留 keyword 兼容
- [√] 1.2 在 `web/src/modules/dictionary/pages/Dictionary.tsx` 拆分筛选字段并新增弹窗表单
- [√] 1.3 在 `web/mock/rules.ts` 与 `web/mock/dictionary.ts` 同步新增筛选规则

## 2. 文本编辑与列表列宽
- [√] 2.1 在 `web/src/modules/texts/pages/TextEdit.tsx` 保存后返回列表并触发刷新
- [√] 2.2 在 `web/src/modules/texts/pages/TextsList.tsx` 调整列宽（原文/译文扩大，操作列缩小）

## 3. 安全检查
- [√] 3.1 检查新增参数处理与前端交互无敏感信息泄露

## 4. 文档更新
- [√] 4.1 更新 `docs/frontend.md` 与 `helloagents/wiki/modules/dictionary.md` 说明筛选字段变化

## 5. 测试
- [ -] 5.1 手动验证词典筛选/新增弹窗/编辑回跳与列表刷新
