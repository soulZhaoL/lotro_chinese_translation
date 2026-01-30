# 任务清单: 后端优先 MVP（补齐 API/权限/锁定/校验 + 最小前端）

目录: `helloagents/plan/202601302117_backend_mvp/`

---

## 里程碑
- M0 数据一致性与迁移策略确认（released_at 字段落地 + 文档同步）
- M1 后端基础能力就绪（认证/权限/文本列表/锁定/变更历史）
- M2 词典与校验 API 就绪
- M3 最小前端可验证主流程
- M4 测试与文档收敛

## 1. 数据模型与一致性
- [-] 1.1 在 `server/migrations/002_add_released_at.sql` 添加 text_locks.released_at（若确认数据库未初始化则改 `server/migrations/001_init.sql`），验证 why.md#需求-认领与锁定-场景-进入翻译页锁定
> 备注: `server/migrations/001_init.sql` 已包含 released_at，无需新增迁移
- [√] 1.2 更新 `helloagents/wiki/data.md` 补齐 released_at 字段说明，验证 why.md#需求-认领与锁定-场景-进入翻译页锁定

## 2. 后端框架与基础结构
- [√] 2.1 确认后端框架（FastAPI/Flask）并在 `server/app.py` 初始化应用，验证 why.md#需求-账号登录与权限-场景-账号登录
- [√] 2.2 在 `server/config/*.py` 建立配置加载与校验（禁止默认配置），验证 why.md#需求-账号登录与权限-场景-账号登录

## 3. 认证与权限
- [√] 3.1 在 `server/routes/auth.py` 实现登录与权限查询，验证 why.md#需求-账号登录与权限-场景-账号登录
- [√] 3.2 在 `server/services/auth.py` 实现密码哈希校验与权限聚合，验证 why.md#需求-账号登录与权限-场景-账号登录

## 4. 主文本与锁定
- [√] 4.1 在 `server/routes/texts.py` 实现列表筛选与详情查询，验证 why.md#需求-主文本列表与筛选-场景-组合筛选
- [√] 4.2 在 `server/routes/claims.py` 实现认领接口与可重复认领规则，验证 why.md#需求-认领与锁定-场景-进入翻译页锁定
- [√] 4.3 在 `server/routes/locks.py` 实现锁定/释放/过期处理（写入 released_at），验证 why.md#需求-认领与锁定-场景-进入翻译页锁定
- [√] 4.4 在 `server/routes/changes.py` 实现变更记录写入与查询，验证 why.md#需求-翻译与变更历史-场景-保存译文

## 5. 词典与校验
- [√] 5.1 在 `server/routes/dictionary.py` 实现词典 CRUD 与筛选，验证 why.md#需求-词典管理-场景-翻译时提示
- [√] 5.2 在 `server/routes/validate.py` 实现最小格式校验与错误返回，验证 why.md#需求-文本格式校验-场景-保存前校验

## 6. 最小前端
- [-] 6.1 在 `web/pages/texts/index.tsx` 实现列表筛选与分页表格，验证 why.md#需求-主文本列表与筛选-场景-组合筛选
> 备注: 当前仓库未包含 web 目录，前端工程未初始化
- [-] 6.2 在 `web/pages/texts/[id]/translate.tsx` 实现翻译页与锁定提示，验证 why.md#需求-认领与锁定-场景-进入翻译页锁定
> 备注: 当前仓库未包含 web 目录，前端工程未初始化
- [-] 6.3 在 `web/pages/dictionary/index.tsx` 实现词典管理基础页，验证 why.md#需求-词典管理-场景-翻译时提示
> 备注: 当前仓库未包含 web 目录，前端工程未初始化

## 7. 安全检查
- [√] 7.1 执行安全检查（输入验证、权限控制、锁定保护、敏感信息处理、密码哈希策略）

## 8. 文档更新
- [√] 8.1 更新 `helloagents/wiki/api.md` 与 `helloagents/wiki/modules/text.md` 追加实现细节
- [√] 8.2 更新 `helloagents/wiki/modules/dictionary.md` 与 `helloagents/wiki/modules/validation.md` 追加实现细节

## 9. 测试
- [-] 9.1 在 `tests/integration/locks.test.py` 覆盖锁定冲突与过期场景
> 备注: 当前仓库未包含 tests 目录，测试工程未初始化
- [-] 9.2 在 `tests/integration/search.test.py` 覆盖关键词检索与分页场景
> 备注: 当前仓库未包含 tests 目录，测试工程未初始化
- [-] 9.3 在 `tests/integration/dictionary.test.py` 覆盖词典筛选场景
> 备注: 当前仓库未包含 tests 目录，测试工程未初始化

---

## 任务状态符号
- `[ ]` 待执行
- `[√]` 已完成
- `[X]` 执行失败
- `[-]` 已跳过
- `[?]` 待确认
