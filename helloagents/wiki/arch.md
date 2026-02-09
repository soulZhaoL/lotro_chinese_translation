# 架构设计

## 总体架构
```mermaid
flowchart TD
    UI[前端界面] --> API[后端服务]
    API --> DB[(PostgreSQL)]
```

## 技术栈
- **后端:** Python + FastAPI
- **前端:** React + Ant Design + Vite
- **数据:** PostgreSQL

## 核心流程
```mermaid
sequenceDiagram
    participant U as 用户
    participant UI as 前端
    participant API as 后端
    participant DB as 数据库

    U->>UI: 查看文本列表
    UI->>API: 查询文本与筛选条件
    API->>DB: 读取主文本与认领信息
    DB-->>API: 返回列表数据
    API-->>UI: 返回列表结果
    U->>UI: 进入翻译页(锁定)
    UI->>API: 申请锁定
    API->>DB: 写入锁定记录
    DB-->>API: 返回锁定状态
    API-->>UI: 返回锁定成功/失败
```

## 维护模式
- 后端以全局中间件拦截所有请求，仅放行 /health 白名单，用于维护窗口与全员下线。
- 前端在维护状态下统一渲染维护页面，禁止进入登录或业务页面。

## 重大架构决策
完整的ADR存储在各变更的how.md中，本章节提供索引。

| adr_id | title | date | status | affected_modules | details |
|--------|-------|------|--------|------------------|---------|
| ADR-001 | 初始架构与数据模型方案 | 2026-01-30 | ✅已采纳 | 用户与权限、文本任务与翻译、词典管理、文本校验 | 待方案包生成 |
| ADR-002 | 后端框架选择（FastAPI） | 2026-01-30 | ✅已采纳 | 后端基础 | history/2026-01/202601302117_backend_mvp/how.md#adr-002 |
| ADR-003 | 前端 Mock 方案（vite-plugin-mock） | 2026-01-30 | ✅已采纳 | 前端 UI | history/2026-01/202601302309_docs_mock_layout/how.md#adr-003 |
| ADR-004 | 维护模式采用配置开关 + 全局中间件 | 2026-02-09 | ✅已采纳 | 用户与权限、后端基础、前端应用 | history/2026-02/202602091037_maintenance_mode/how.md#adr-004-维护模式采用配置开关--全局中间件 |
