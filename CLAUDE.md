# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个 LOTRO（指环王 Online）游戏文本的中文翻译协作系统，包含后端 API 服务和前端 Web 界面。

## 技术栈

**后端:**
- Python 3.11+ + FastAPI + uvicorn
- MySQL 8.0+ (PyMySQL)
- 配置管理: PyYAML + python-dotenv

**前端:**
- React 18 + TypeScript + Vite
- Ant Design 5 + @ant-design/pro-components
- vite-plugin-mock (仅开发环境)

## 核心架构

### 后端结构 (server/)
- `app.py` - FastAPI 应用入口，路由注册，全局中间件（CORS、GZip、维护模式）
- `db.py` - 数据库连接管理，提供 `db_cursor()` 和 `db_stream_cursor()` 上下文管理器
- `config/loader.py` - 配置加载与校验，从 `config/lotro.yaml` 读取配置，通过环境变量注入敏感信息
- `routes/` - API 路由模块
  - `texts.py` - 主文本列表、详情、翻译、导入导出（Excel）
  - `claims.py` - 文本认领与释放
  - `locks.py` - 文本编辑锁定
  - `dictionary.py` - 词典管理
  - `changes.py` - 文本变更历史
  - `auth.py` - 用户认证（基于 HMAC token）
  - `validate.py` - 文本模板校验
  - `health.py` - 健康检查
- `services/` - 业务逻辑层
  - `auth.py` - 认证服务（密码哈希、token 生成与验证）
  - `maintenance.py` - 维护模式管理
- `response.py` - 统一响应格式封装

### 前端结构 (web/)
- `src/pages/` - 页面组件（登录、主文本列表、词典等）
- `src/api.ts` - 统一 API 请求封装
- `mock/` - Mock 数据（仅开发环境）
- `vite.config.ts` - Vite 配置，支持多环境（mock/test/production）

### 数据库核心表
- `text_main` - 主文本表（fid, textId, part, sourceText, translatedText, status, isClaimed）
- `text_claims` - 文本认领记录
- `text_locks` - 文本编辑锁定
- `text_changes` - 文本变更历史
- `dictionary_entries` - 词典条目
- `users` - 用户表

### 工具脚本 (tools/)
- `version_iteration_tool/` - 版本迭代工具（7步流程，用于游戏版本更新时的文本库迁移）
  - 执行顺序: step1 → step2 → step3 → step4 → run_step5_to_step7.py
  - 详细流程参考 `docs/db_version_iteration_runbook.md`
- `valid_format/` - Excel 格式校验与导入工具

## 配置管理原则

**严格禁止默认配置:**
- 所有配置必须来自 `config/lotro.yaml`
- 敏感信息通过环境变量注入（`LOTRO_DATABASE_DSN`, `LOTRO_TOKEN_SECRET`）
- 配置缺失时必须直接报错，禁止使用 fallback 默认值
- 环境变量通过 `.env` 文件加载（项目根目录），或通过 `LOTRO_ENV_PATH` 指定路径

## 常用命令

### 后端开发

**安装依赖:**
```bash
pip install -r requirements.txt
```

**启动开发服务（一键启动 SSH 隧道 + 后端）:**
```bash
./server/start_dev.sh --env .env
```

**手动启动:**
```bash
# 先启动 SSH 隧道（如需连接远程数据库）
ssh -N -L 5433:127.0.0.1:3306 ubuntu@<host> -p 22

# 启动后端
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

**运行测试:**
```bash
pytest -q                              # 运行所有测试
pytest tests/tmp_test_locks.py -q     # 运行单个测试文件
```

**数据库迁移:**
```bash
mysql --defaults-extra-file=/path/to/mysql.cnf < server/migrations/001_init.sql
```

### 前端开发

**安装依赖:**
```bash
cd web && npm install
```

**启动开发服务:**
```bash
npm run dev:mock    # Mock 模式（不依赖后端）
npm run dev:test    # 测试模式（连接测试环境后端）
npm run dev         # 默认模式
```

**构建生产版本:**
```bash
npm run build:prod  # 生产环境构建
npm run build:test  # 测试环境构建
```

## 关键设计决策

### 数据库连接
- 使用 `db_cursor()` 进行普通查询（自动提交事务）
- 使用 `db_stream_cursor()` 进行大数据量流式查询（如 Excel 导出）
- DSN 格式: `mysql://user:password@host:port/database?charset=utf8mb4`
- 所有连接强制启用 ANSI_QUOTES 模式

### 认证机制
- 基于 HMAC-SHA256 的无状态 token
- token 包含 userId 和过期时间，由 `LOTRO_TOKEN_SECRET` 签名
- 密码使用 SHA256 + 随机盐哈希存储
- 全员下线方案: 更换 `LOTRO_TOKEN_SECRET` 并重启服务

### 维护模式
- 通过 `config/lotro.yaml` 的 `maintenance.enabled` 控制
- 全局中间件拦截所有请求，仅放行白名单路径（如 `/health`）
- 用于版本迭代时的数据库换表操作

### Excel 导入导出
- 固定表头: `("编号", "FID", "TextId", "Part", "原文", "译文", "状态")`
- 状态映射: `{"新增": 1, "修改": 2, "已完成": 3}`
- 导出使用流式查询 + 分批写入，避免内存溢出
- 导入支持批量校验与插入

### 版本迭代流程
版本更新（如 U46 → U46.1）时执行 7 步流程，核心策略:
1. 备份 `text_main` 为 `text_main_bak_<version>`
2. 在 `text_main_next` 中构建新版本
3. 通过 `sourceTextHash` 比对原文变化，继承译文
4. 清空 `text_claims` 和 `text_locks`
5. 按 ID 映射迁移 `text_changes`
6. 原子切换 `text_main_next` → `text_main`
7. 详细流程见 `docs/db_version_iteration_runbook.md`

## 代码约定

### 命名规范
- 数据库列名、API 字段、前后端变量统一使用 camelCase
- 临时文件必须以 `tmp_` 前缀命名
- 临时文件必须放置在 `项目根目录/tmp/` 目录下

### 错误处理
- 分析问题根本原因，而非症状
- 禁止用 try-except 掩盖真正的 bug
- 宁可程序报错失败，也不要返回错误结果

### 测试约定
- 测试文件使用 `tmp_test_*.py` 命名
- pytest 配置在 `pytest.ini` 中
- 使用 `@pytest.mark.no_db` 标记不依赖数据库的测试

## 文档位置

- 后端使用说明: `docs/backend.md`
- 前端使用说明: `docs/frontend.md`
- 版本迭代手册: `docs/db_version_iteration_runbook.md`
- API 文档: `helloagents/wiki/api.md`
- 架构设计: `helloagents/wiki/arch.md`
- 数据模型: `helloagents/wiki/data.md`
- 项目技术约定: `helloagents/project.md`

## 注意事项

- 前端 Mock 模式仅限本地开发，生产环境必须禁用（`VITE_USE_MOCK=false`）
- 版本迭代必须在维护窗口内执行，并强制全员下线
- 所有配置变更后必须重启服务才能生效
- SSH 隧道用于本地开发连接远程数据库，生产环境直连
