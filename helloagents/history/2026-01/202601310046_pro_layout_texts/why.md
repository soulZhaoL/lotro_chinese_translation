# 变更提案: Pro 风格前端 + 文本列表增强 + API/Mock 对齐

## 需求背景
当前前端 UI/布局与目标风格不一致，文本列表功能缺失。需要采用 Ant Design Pro 风格（ProLayout/ProTable），完善查询与操作入口，并确保 Mock 与后端 API 完全一致。

## 变更内容
1. 前端采用 Ant Design Pro 风格布局与组件（ProLayout/ProTable）
2. 文本列表增加查询字段与操作入口（认领/释放/编辑/详情/更新记录）
3. 按功能模块创建对应页面
4. 后端 API 增补与前端 Mock 对齐，确保字段一致

## 影响范围
- **模块:** 前端 UI、文本任务与翻译、变更记录、认领与锁定
- **文件:** web/src/*, web/mock/*, server/routes/*, helloagents/wiki/api.md
- **API:** /texts, /texts/{id}, /claims, /locks, /changes, 新增文本编辑接口
- **数据:** text_main/text_changes/text_claims/text_locks

## 核心场景

### 需求: Pro 风格布局
**模块:** 前端 UI
采用 Ant Design Pro 风格（顶部导航 + 左侧菜单 + 内容区）

#### 场景: 页面导航
- 顶部显示系统级导航
- 左侧显示模块导航

### 需求: 文本列表增强
**模块:** 文本任务与翻译
支持 fid/状态/原文关键字/汉化关键字/更新时间范围/认领人/是否认领查询

#### 场景: 查询与操作
- 列表支持详情入口（编号）
- 操作包含认领/释放/编辑/更新记录

### 需求: API/Mock 一致性
**模块:** 后端/Mock
新增或补齐接口，Mock 与 API 完全一致

#### 场景: 前后端联调
- Mock 与真实后端字段一致
- 可切换 Mock 与真实 API

## 风险评估
- **风险:** 新增 API 影响现有流程
- **缓解:** 明确接口定义与字段，优先保持向后兼容
