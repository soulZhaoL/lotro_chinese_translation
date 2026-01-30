# Changelog

本文件记录项目所有重要变更。
格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/),
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 新增
- 初始数据库迁移脚本（用户/文本/认领/锁定/变更/词典）
- FastAPI 后端骨架与核心接口（认证/文本/锁定/词典/校验）
- YAML 配置文件与依赖清单
- 前端工程骨架（React + Ant Design + Vite）
- 后端集成测试骨架（pytest）
- .env 配置加载与敏感信息占位支持
- docs 使用说明与 MVP 联通指引
- 前端 Mock（vite-plugin-mock）
- 后端单元测试补充（锁定/搜索/词典/校验）

### 变更
- 配置文件路径固定为 `config/lotro.yaml`，不再依赖 LOTRO_CONFIG_PATH
- 前端布局调整为顶部导航 + 左侧二级

### 修复
- 数据模型文档补齐 text_locks.released_at 字段

## [0.1.0] - 2026-01-30

### 新增
- 初始化知识库文档结构
