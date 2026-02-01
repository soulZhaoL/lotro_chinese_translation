# 项目技术约定

---

## 技术栈
- **核心:** Python + FastAPI / React + Ant Design + Vite
- **前端工具:** vite-plugin-mock
- **前端组件:** @ant-design/pro-components
- **数据:** PostgreSQL

---

## 开发约定
- **代码规范:** 待定（建议后端 PEP 8，前端 ESLint + Prettier）
- **命名约定:** 后端 snake_case，前端 camelCase

---

## 错误与日志
- **策略:** 统一错误码与可读错误信息
- **日志:** 分级日志（INFO/WARN/ERROR），包含请求ID

---

## 测试与流程
- **测试:** 关键流程需具备最小回归测试
- **提交:** 语义化提交（如 feat/fix/docs）

## 配置管理
- **配置文件:** 固定使用 `config/lotro.yaml`
- **环境变量:** 支持 `.env`（默认读取项目根目录或通过 `LOTRO_ENV_PATH` 指定）
- **默认值:** 禁止默认配置，缺失即报错
