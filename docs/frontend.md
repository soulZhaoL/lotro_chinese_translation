# 前端使用说明

## 环境依赖
- Node.js 18+
- pnpm / npm / yarn（任选其一）

## 安装依赖
在 `web/` 目录执行：
```
npm install
```

## 配置说明（运行时配置，适配 Vercel）
前端运行时读取 `web/public/app-config.json`（需随部署产物一起发布）：
```json
{
  "apiBaseUrl": "https://your-api-domain.example.com",
  "useMock": false
}
```
- `apiBaseUrl`: 后端服务地址
- `useMock`: 是否启用 Mock（true/false）

> 提示：`app-config.json.example` 为模板，部署前请复制并修改为 `app-config.json`。
> Vercel 部署时可直接提交 `app-config.json`，或在构建前通过脚本生成该文件。

## 启动开发服务
```
npm run dev
```

## Mock 使用
- `useMock=true` 时，前端请求会走本地 Mock 数据
- `useMock=false` 时，前端请求走真实后端接口
- Mock 数据需与后端接口结构保持一致，避免联通阶段对不上

## 安全提示（Mock 仅限开发）
- `vite-plugin-mock` 依赖 `mockjs`，存在已知高危漏洞且暂无修复版本
- 仅允许在本地开发环境使用 Mock，不可在生产环境启用
- 生产部署必须使用 `npm run build` 的静态产物，不允许暴露 Vite dev server
## 安全提示
如需修复 npm audit 提示的漏洞，升级 vite-plugin-mock 至 3.x 后重新安装依赖。

## 目录结构
- `web/src/pages/` 页面
- `web/mock/` Mock 数据
- `web/src/api.ts` 统一 API 请求封装

## 界面风格
- 使用 Ant Design Pro Components（ProLayout/ProTable）
- 主文本列表支持高级查询与操作入口
- 菜单已补充图标，退出按钮位于头像与用户名之后

## 主文本列表功能
查询字段:
- fid
- 状态
- 原文关键字
- 汉化关键字
- 更新时间范围
- 认领人
- 是否认领

操作入口:
- 认领
- 释放
- 编辑
- 详情（编号入口）
- 更新记录

列表字段:
- 原文（>200 截断，hover 展示全文，>2000 继续截断）
- 译文（>200 截断，hover 展示全文，>2000 继续截断）
- 编辑次数

## 词典功能
- 分类使用枚举映射展示（如 skill -> 技能）
- 分类筛选使用下拉选择框
- 查询条件分为原文与译文两个输入框
- 新增按钮使用弹窗表单，保存成功后刷新列表

## 交互提示
- 登录/认领/释放/保存/新增等操作有成功与失败提示

## 常见问题
- 无法访问接口：确认 `VITE_API_BASE_URL` 指向正确地址
- Mock 未生效：确认 `VITE_USE_MOCK=true` 并重启 `npm run dev`
