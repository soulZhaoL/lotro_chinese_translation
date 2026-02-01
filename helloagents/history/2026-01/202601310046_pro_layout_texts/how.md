# 技术设计: Pro 风格前端 + 文本列表增强 + API/Mock 对齐

## 技术方案

### 核心技术
- 前端: Ant Design Pro Components（ProLayout/ProTable/ProForm）
- 后端: FastAPI
- Mock: vite-plugin-mock

### 实现要点
- 使用 ProLayout 构建顶部+左侧布局
- 使用 ProTable 实现查询表格与操作列
- 查询字段映射为 API query 参数
- 新增/补齐后端接口，并同步 Mock

## API 设计
- GET /texts
  - query: fid/status/source_keyword/translated_keyword/updated_from/updated_to/claimer/claimed
- GET /texts/{id}
- POST /claims
- DELETE /claims/{id} （释放认领）
- POST /locks
- DELETE /locks/{id}
- GET /changes?text_id=...
- PUT /texts/{id}/translate （保存译文并写入变更记录）

## 安全与性能
- 查询参数全部校验
- 避免开放未授权接口

## 测试与部署
- 使用现有 pytest 框架补充接口测试
- 前端 Mock 与真实 API 严格一致
