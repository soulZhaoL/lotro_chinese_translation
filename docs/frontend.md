# 前端使用说明

## 环境依赖
- Node.js 18+
- pnpm / npm / yarn（任选其一）

## 安装依赖
在 `web/` 目录执行：
```
npm install
```

## 配置说明
`web/.env.example` 为前端配置模板，复制为 `web/.env` 后修改：
```
VITE_API_BASE_URL=http://localhost:8000
VITE_USE_MOCK=true
```

- `VITE_API_BASE_URL`: 指向后端服务地址
- `VITE_USE_MOCK`: 是否启用 Mock（true/false）

## 启动开发服务
```
npm run dev
```

## Mock 使用
- `VITE_USE_MOCK=true` 时，前端请求会走本地 Mock 数据
- `VITE_USE_MOCK=false` 时，前端请求走真实后端接口
- Mock 数据需与后端接口结构保持一致，避免联通阶段对不上

## 目录结构
- `web/src/pages/` 页面
- `web/mock/` Mock 数据
- `web/src/api.ts` 统一 API 请求封装

## 常见问题
- 无法访问接口：确认 `VITE_API_BASE_URL` 指向正确地址
- Mock 未生效：确认 `VITE_USE_MOCK=true` 并重启 `npm run dev`
