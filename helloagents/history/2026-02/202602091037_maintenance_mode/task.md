# 任务清单: 维护模式与全员下线

目录: `helloagents/plan/202602091037_maintenance_mode/`

---

## 1. 后端维护模式拦截
- [√] 1.1 在 `config/lotro.yaml` 与 `server/config/loader.py` 中新增 maintenance 配置分组并完成类型校验与布尔解析，验证 why.md#需求-维护模式全局拦截-场景-维护期开启
- [√] 1.2 新增 `server/services/maintenance.py` 并在 `server/app.py` 中加入全局维护中间件，维护期开启时返回 503/MAINTENANCE 响应，验证 why.md#需求-维护模式全局拦截-场景-维护期开启
- [√] 1.3 在 `server/routes/health.py` 返回 maintenance 标记，并在维护中间件中保留 /health 白名单，验证 why.md#需求-维护模式全局拦截-场景-维护期开启

## 2. 前端维护页面与全局守卫
- [√] 2.1 新增 `web/src/pages/Maintenance.tsx` 并在 `web/src/App.tsx` 中全局渲染维护页面（优先于登录与路由），验证 why.md#需求-维护模式全局拦截-场景-维护期开启
- [√] 2.2 新增 `web/src/maintenance.ts`，并更新 `web/src/api.ts` 与 `web/src/main.tsx` 完成维护状态探测与全局事件通知，验证 why.md#需求-维护模式全局拦截-场景-维护期开启

## 3. 安全检查
- [√] 3.1 进行维护模式安全审计（输入验证、敏感信息处理、权限控制、EHRB 风险规避），记录结果在方案执行日志中
  > 备注: 维护模式仅由配置驱动，不新增管理接口；统一返回 503/MAINTENANCE，不暴露敏感信息；/health 白名单限制为只读；EHRB 风险控制点为 token_secret 轮换需人工运维确认。

## 4. 文档更新
- [√] 4.1 更新 `helloagents/wiki/modules/user.md`、`helloagents/wiki/arch.md` 与 `helloagents/CHANGELOG.md`，记录维护模式与全员下线机制，验证 why.md#需求-全员下线与暂停登录-场景-切换维护窗口

## 5. 测试
- [√] 5.1 新增 `tests/test_maintenance.py` 覆盖维护开启/关闭与 /health 白名单场景，验证 why.md#需求-维护模式全局拦截-场景-维护期开启
