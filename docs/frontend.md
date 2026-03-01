# 前端使用说明

## 环境依赖
- Node.js 18+
- pnpm / npm / yarn（任选其一）

## 安装依赖
在 `web/` 目录执行：
```
npm install
```

## 三阶段生命周期（mock -> test -> prod）
前端统一使用 `VITE_*` 变量，并由 Vite 在构建时注入：

- `VITE_API_BASE_URL`: 后端服务地址（例如 `https://api.example.com`）
- `VITE_USE_MOCK`: 是否启用 Mock，仅支持 `true/false`

### 阶段 1：Mock 开发
目标：前端独立开发，全部走 mock 数据。

1. 复制配置文件：
```bash
cp web/.env.mock.example web/.env.mock
```
2. 启动：
```bash
cd web && npm run dev:mock
```
3. 约束：
- `VITE_USE_MOCK=true`
- 此阶段不依赖测试/生产后端可用性

### 阶段 2：联调测试（连接测试环境后端）
目标：前端本地项目连接测试环境服务，验证接口与业务流程。

1. 复制配置文件并填写测试 API：
```bash
cp web/.env.test.example web/.env.test
```
2. 启动：
```bash
cd web && npm run dev:test
```
3. 约束：
- `VITE_USE_MOCK=false`
- `VITE_API_BASE_URL` 必须指向测试环境地址

### 阶段 3：生产部署（Vercel）
目标：构建生产产物并部署线上。

1. Vercel 环境变量（Production）：
- `VITE_USE_MOCK=false`
- `VITE_API_BASE_URL=https://your-api-domain.example.com`
2. 本地可先做生产构建验证：
```bash
cd web && npm run build:prod
```
3. 在 Vercel 重新触发部署（变量变更后必须重新部署）。

## 命令清单
- `npm run dev:mock`：mock 开发模式（`--mode mock`）
- `npm run dev:test`：测试联调模式（`--mode test`）
- `npm run build:test`：测试环境构建（`--mode test`）
- `npm run build:prod`：生产环境构建（`--mode production`）
- `npm run dev` / `npm run build`：默认模式（沿用 `.env`）

## 配置约束
- 所有构建命令（`vite build`）都禁止 `VITE_USE_MOCK=true`
- `VITE_USE_MOCK=false` 时，`VITE_API_BASE_URL` 不能为空
- 开发态（`vite serve`）可通过 `VITE_USE_MOCK=true` 打开 mock

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
- 无法访问接口：确认 `VITE_API_BASE_URL` 指向正确地址，并重新部署
- Mock 未生效：确认 `VITE_USE_MOCK=true` 且运行在 `npm run dev:mock`
