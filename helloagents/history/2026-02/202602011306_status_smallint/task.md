# 任务清单: 文本状态改为数值枚举

目录: `helloagents/plan/202602011306_status_smallint/`

---

## 1. 数据库结构
- [√] 1.1 在 `server/migrations/001_init.sql` 中将 status 改为 SMALLINT，并更新默认值/约束/注释

## 2. 后端接口
- [√] 2.1 在 `server/routes/texts.py` 中将 status 筛选参数改为 int，并校验 1/2/3
- [√] 2.2 保存译文时按完成状态更新 status（完成=3，未完成=2）

## 3. 前端与 Mock
- [√] 3.1 更新 `web/src/modules/texts/pages/TextsList.tsx` 状态类型与筛选枚举
- [√] 3.2 更新 `web/src/modules/texts/pages/TextDetail.tsx`、`web/src/pages/Translate.tsx` 类型与展示映射
- [√] 3.3 更新 `web/mock/rules.ts`、`web/mock/texts.ts` 的状态字段为数值

## 4. 工具与配置
- [√] 4.1 更新 `tools/xlsx_to_insert.yaml` 固定 status=1
- [√] 4.2 更新 `tools/xlsx_to_insert.py` 增加 status 固定值校验

## 5. 文档更新
- [√] 5.1 更新 `helloagents/wiki/data.md` 与 `helloagents/wiki/modules/text.md`
- [√] 5.2 更新 `helloagents/wiki/api.md` 与 `helloagents/CHANGELOG.md`

## 6. 安全检查
- [√] 6.1 确认无默认配置回退与硬编码映射
