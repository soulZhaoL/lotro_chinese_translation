# 任务清单: textId拆分与嵌套列表

目录: `helloagents/plan/202602081258_textid_split/`

---

## 1. 数据库结构与导入准备
- [√] 1.1 在 `server/migrations/001_init.sql` 中新增 `text_id` 字段、调整 `part` 为顺序编号类型、移除 `uq_text_main_fid_part` 并补充索引，验证 why.md#需求-父列表嵌套展示-场景-浏览父列表
- [√] 1.2 在 `tools/xlsx_to_insert.yaml` 中新增 `text_id` 列映射，验证 why.md#需求-子列表查询与分页-场景-展开-fid-子列表
- [√] 1.3 在 `tools/xlsx_to_insert.py` 中支持 `text_id` 解析与写入，验证 why.md#需求-子列表查询与分页-场景-展开-fid-子列表

## 2. 后端接口与校验
- [√] 2.1 在 `server/routes/texts.py` 中新增 `/texts/parents` 列表接口（仅 part=1）并保留分页与筛选，验证 why.md#需求-父列表嵌套展示-场景-浏览父列表
- [√] 2.2 在 `server/routes/texts.py` 中新增 `/texts/children` 接口（fid 必填，支持 text_id 查询与分页、按 part 升序），验证 why.md#需求-子列表查询与分页-场景-展开-fid-子列表
- [√] 2.3 在 `server/routes/texts.py` 中新增 `/texts/by-textid` 接口（fid+text_id 精确查询），并对重复 textId 返回 409，验证 why.md#需求-详情编辑按-fidtextid-定位-场景-从子列表进入编辑

## 3. 前端嵌套列表与状态恢复
- [√] 3.1 在 `web/src/modules/texts/pages/TextsList.tsx` 中改为 AntD 嵌套表格：外层请求 parents，子列表请求 children；子列表支持 textId 查询与分页；保存并恢复展开/分页/筛选状态，验证 why.md#需求-父列表嵌套展示-场景-浏览父列表
- [√] 3.2 在 `web/src/App.tsx` 中新增 fid+textId 路由并调整面包屑识别逻辑，验证 why.md#需求-详情编辑按-fidtextid-定位-场景-从子列表进入编辑
- [√] 3.3 在 `web/src/modules/texts/pages/TextDetail.tsx` 中使用 fid+textId 查询接口并显示 textId，验证 why.md#需求-详情编辑按-fidtextid-定位-场景-从子列表进入编辑
- [√] 3.4 在 `web/src/modules/texts/pages/TextEdit.tsx` 中使用 fid+textId 查询接口，保存仍基于内部 id，并在返回时恢复列表状态，验证 why.md#需求-详情编辑按-fidtextid-定位-场景-从子列表进入编辑
- [√] 3.5 在 `web/mock/rules.ts` 与 `web/mock/changes.ts` 中补充 textId 字段与新接口模拟数据，验证 why.md#需求-子列表查询与分页-场景-展开-fid-子列表

## 4. 文档更新
- [√] 4.1 更新 `helloagents/wiki/data.md` 的 text_main 字段与索引描述，验证 why.md#需求-父列表嵌套展示-场景-浏览父列表
- [√] 4.2 更新 `helloagents/wiki/modules/text.md` 的接口与字段说明，验证 why.md#需求-子列表查询与分页-场景-展开-fid-子列表
- [√] 4.3 更新 `helloagents/wiki/api.md`，补充 parents/children/by-textid 接口说明，验证 why.md#需求-详情编辑按-fidtextid-定位-场景-从子列表进入编辑

## 5. 安全检查
- [√] 5.1 执行输入校验与重复数据检测检查（按G9），确认重复 textId 会被阻断并报错

## 6. 测试
- [√] 6.1 在 `tests` 中补充 parents/children/by-textid 的分页与重复校验集成测试，验证点：分页正确、textId 过滤生效、重复返回 409
