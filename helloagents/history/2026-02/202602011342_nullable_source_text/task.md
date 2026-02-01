# 任务清单: 允许原文为空并同步导入

目录: `helloagents/plan/202602011342_nullable_source_text/`

---

## 1. 数据库结构
- [√] 1.1 在 `server/migrations/001_init.sql` 中允许 source_text 为空并补充注释

## 2. 导入配置
- [√] 2.1 更新 `tools/xlsx_to_insert.yaml`，将 source_text 加入 nullable_columns

## 3. 前端类型与展示
- [√] 3.1 更新 `web/src/modules/texts/pages/TextsList.tsx` 的 source_text 类型
- [√] 3.2 更新 `web/src/modules/texts/pages/TextDetail.tsx`/`TextEdit.tsx`/`web/src/pages/Translate.tsx`，对空原文做兜底展示

## 4. 文档更新
- [√] 4.1 更新 `helloagents/wiki/data.md` 与 `helloagents/wiki/modules/text.md`
- [√] 4.2 更新 `helloagents/CHANGELOG.md`

## 5. 安全检查
- [√] 5.1 确认不触发默认配置兜底
