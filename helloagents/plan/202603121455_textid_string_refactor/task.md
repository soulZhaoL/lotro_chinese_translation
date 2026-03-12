# 任务清单: textId 字符串化与全链路修正

目录: `helloagents/plan/202603121455_textid_string_refactor/`

---

## 1. 数据模型与迁移策略
- [x] 1.1 在 `server/migrations/001_init.sql` 中将 `text_main.textId` 从 `BIGINT` 调整为 `VARCHAR`，并同步检查唯一约束/索引定义，验证 why.md#需求-按字符串-textid-精确查询与筛选-场景-通过复合-textid-查询
- [x] 1.2 产出"错误 fid+textId → 正确 fid+textId"的对照结果生成方案，并实现可导出的映射结果（SQL/脚本/临时表），验证 why.md#需求-生成错误正确-textid-对照结果-场景-生成修复映射（实现: tools/fix_textid/generate_textid_fix_map.py，已修正正则使其提取完整字符串 textId，输出 CSV + UPDATE SQL）
- [x] 1.3 评估并确认 80 万行下 `textId` 改为字符串后的索引保留策略，输出到知识库与方案实现中，验证 why.md#需求-字符串-textid-索引可支撑-80-万行查询-场景-评估索引保留策略（结论见 how.md ADR-003，SQL 已含正确索引定义）
- [x] 1.4 在 `helloagents/wiki/data.md` 中更新 `text_main.textId` 与相关索引的数据模型说明，验证 why.md#需求-字符串-textid-索引可支撑-80-万行查询-场景-评估索引保留策略

## 2. 工具链解析修正
- [x] 2.1 在 `tools/valid_format/xlsx_to_insert_segmented.py` 中修改协议段解析逻辑，使三类协议都返回完整字符串 textId，并同步更新行构造类型，验证 why.md#需求-协议段完整提取-textid-场景-解析复合协议头（_build_patterns 已修正：格式2/3 的 textId 命名组现包含完整 `:::n`/`:::m-n` 部分）
- [x] 2.2 在 `tools/version_iteration_tool/step4_generate_text_main_next_insert.py` 中修改协议段解析逻辑，使 Step4 生成 SQL 时写入完整字符串 textId，验证 why.md#需求-协议段完整提取-textid-场景-解析复合协议头（_build_patterns 已修正：格式2/3 的 textId 命名组现包含完整 `:::n`/`:::m-n` 部分）
- [x] 2.3 复查 `tools/valid_format/xlsx_to_insert.py` 与相关配置/注释，明确其是否继续使用、是否需要同步支持字符串 textId，验证 why.md#需求-协议段完整提取-textid-场景-解析复合协议头（结论：该工具不解析协议段，无需修改）

## 3. 版本迭代链路修正
- [x] 3.1 在 `tools/version_iteration_tool/step5_compare_and_inherit.sql` 中确认 `(fid,textId)` 比对逻辑适配字符串 textId，并补充必要字段类型调整，验证 why.md#需求-版本迭代按真实业务键继承历史数据-场景-版本升级后继承旧译文（结论：JOIN 逻辑无类型硬编码，代码层面正确；运维需注意备份表字段类型）
- [x] 3.2 在 `tools/version_iteration_tool/step6_create_text_id_map.sql` 中将 map 表 `textId` 改为字符串类型，并保持 `(fid,textId)` 唯一键，验证 why.md#需求-版本迭代按真实业务键继承历史数据-场景-版本升级后继承旧译文
- [x] 3.3 复查 `tools/version_iteration_tool/run_step5_to_step7.py`、README 与 Step7 相关文件，确保执行说明与字符串 textId 语义一致，验证 why.md#需求-版本迭代按真实业务键继承历史数据-场景-版本升级后继承旧译文（结论：Python 实现中 JOIN 逻辑无类型假设，无需修改）

## 4. 后端接口与类型修正
- [x] 4.1 在 `server/routes/texts.py` 中将列表、下载、children、by-textid 的 `textId` 查询参数统一改为字符串，并移除数值型假设，验证 why.md#需求-按字符串-textid-精确查询与筛选-场景-通过复合-textid-查询
- [x] 4.2 复查 `server/routes/validate.py`、`server/routes/changes.py`、`server/routes/claims.py`、`server/routes/locks.py` 中与业务 textId 混淆的逻辑，区分内部 `id` 与业务 `textId`（各路由的 textId 字段已改名为 id，明确语义）
- [x] 4.3 更新 `helloagents/wiki/api.md` 与 `helloagents/wiki/modules/text.md` 的接口参数与响应说明，验证 why.md#需求-按字符串-textid-精确查询与筛选-场景-通过复合-textid-查询

## 5. 前端筛选与页面修正
- [x] 5.1 在 `web/src/modules/texts/types.ts`、`web/src/modules/texts/list/filter.tsx`、`web/src/modules/texts/list/index.tsx`、`web/src/modules/texts/list/table.tsx` 中统一 textId 为字符串查询语义，验证 why.md#需求-按字符串-textid-精确查询与筛选-场景-通过复合-textid-查询
- [x] 5.2 复查 `web/src/modules/texts/detail/index.tsx`、`web/src/modules/texts/edit/index.tsx`、`web/src/App.tsx` 与相关路由参数，确保复合 textId 能稳定传递与查询，验证 why.md#需求-按字符串-textid-精确查询与筛选-场景-通过复合-textid-查询
- [x] 5.3 复查 `web/src/pages/Translate.tsx` 与 `web/mock/*`，区分内部 id 与业务 textId，避免新旧语义继续混淆（mock 中 textId 类型改为 string，/changes 和 /claims /locks API 参数改为 id）

## 6. 安全检查
- [x] 6.1 执行全链路检查，确认不存在 `int(textId)`、`Number(textId)`、`BIGINT textId`、正则只截取数字前缀等残留实现（已清除所有 mock 和后端的数值型 textId 假设；ChangeItem.textId 保持 number 因为是内部 FK）

## 7. 测试与验证
- [ ] 7.1 在相关测试中补充复合 textId 用例，覆盖工具解析、后端查询、前端筛选与版本迭代关键路径，验证 why.md#需求-协议段完整提取-textid-场景-解析复合协议头
- [ ] 7.2 基于一条示例复合 textId（如 `126853056:::337429-296068`）做端到端验证清单，确认导入、查询、导出、详情定位与版本继承一致，验证 why.md#需求-版本迭代按真实业务键继承历史数据-场景-版本升级后继承旧译文
- [ ] 7.3 生成错误/正确 textId 对照结果后，抽样核对映射准确性，并准备全局 update 执行说明，验证 why.md#需求-生成错误正确-textid-对照结果-场景-生成修复映射
