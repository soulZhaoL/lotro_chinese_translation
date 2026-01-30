# 任务清单: LOTRO 文本汉化系统 MVP

目录: `helloagents/plan/202601301800_translation_mvp/`

---

## 1. 数据模型与索引
- [ ] 1.1 在 `server/migrations/001_init.sql` 中定义用户/权限、主文本、认领、锁定、变更历史、词典表，验证 why.md#需求-用户管理-场景-账号登录
- [ ] 1.2 在 `server/migrations/001_init.sql` 中建立 fid/part/status/更新时间索引与关键词检索索引，验证 why.md#需求-主文本列表与筛选-场景-组合筛选
- [ ] 1.3 在 `server/migrations/001_init.sql` 中添加单活锁约束与认领唯一约束，验证 why.md#需求-认领与锁定-场景-进入翻译页锁定

## 2. 后端接口
- [ ] 2.1 在 `server/routes/auth.py` 实现登录与权限查询，验证 why.md#需求-用户管理-场景-账号登录
- [ ] 2.2 在 `server/routes/texts.py` 实现列表筛选与详情查询（含分页与关键词），验证 why.md#需求-主文本列表与筛选-场景-组合筛选
- [ ] 2.3 在 `server/routes/claims.py` 实现认领接口与可重复认领规则，验证 why.md#需求-认领与锁定-场景-进入翻译页锁定
- [ ] 2.4 在 `server/routes/locks.py` 实现锁定/释放与过期处理，验证 why.md#需求-认领与锁定-场景-进入翻译页锁定
- [ ] 2.5 在 `server/routes/changes.py` 实现变更记录写入与查询，验证 why.md#需求-翻译与变更历史-场景-查看变更历史
- [ ] 2.6 在 `server/routes/dictionary.py` 实现词典 CRUD 与筛选，验证 why.md#需求-词典高亮与数量提示-场景-翻译时提示
- [ ] 2.7 在 `server/routes/validate.py` 实现格式校验占位与错误返回，验证 why.md#需求-文本格式校验-场景-保存前校验

## 3. 前端页面与交互
- [ ] 3.1 在 `web/pages/texts/index.tsx` 实现列表筛选与分页表格，验证 why.md#需求-主文本列表与筛选-场景-组合筛选
- [ ] 3.2 在 `web/pages/texts/[id].tsx` 实现详情页（原文/译文/认领信息），验证 why.md#需求-翻译与变更历史-场景-查看变更历史
- [ ] 3.3 在 `web/pages/texts/[id]/translate.tsx` 实现翻译页（锁定提示、左右布局），验证 why.md#需求-认领与锁定-场景-进入翻译页锁定
- [ ] 3.4 在 `web/pages/texts/[id]/changelog.tsx` 实现变更历史左右对比布局，验证 why.md#需求-翻译与变更历史-场景-查看变更历史
- [ ] 3.5 在 `web/pages/dictionary/index.tsx` 实现词典管理与高亮预览，验证 why.md#需求-词典高亮与数量提示-场景-翻译时提示
- [ ] 3.6 在 `web/pages/users/index.tsx` 实现用户与权限管理基础页，验证 why.md#需求-用户管理-场景-账号登录

## 4. 词典高亮与数量提示
- [ ] 4.1 在 `web/components/DictionaryHighlighter.tsx` 实现原文 key 高亮、译文 value 高亮与数量一致性提示，验证 why.md#需求-词典高亮与数量提示-场景-翻译时提示

## 5. 安全检查
- [ ] 5.1 执行安全检查（输入验证、权限控制、锁定保护、敏感信息处理）

## 6. 文档更新
- [ ] 6.1 更新 `helloagents/wiki/data.md` 与 `helloagents/wiki/api.md` 同步实现细节
- [ ] 6.2 更新 `helloagents/wiki/modules/text.md` 与 `helloagents/wiki/modules/dictionary.md` 追加实施说明

## 7. 测试
- [ ] 7.1 在 `tests/integration/locks.test.py` 中覆盖锁定冲突与过期场景
- [ ] 7.2 在 `tests/integration/search.test.py` 中覆盖关键词检索与分页场景
- [ ] 7.3 在 `tests/integration/dictionary.test.py` 中覆盖词典数量提示场景
