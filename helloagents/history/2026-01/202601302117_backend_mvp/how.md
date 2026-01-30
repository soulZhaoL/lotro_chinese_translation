# 技术设计: 后端优先 MVP（补齐 API/权限/锁定/校验 + 最小前端）

## 技术方案

### 核心技术
- Python + FastAPI
- PostgreSQL
- React + Ant Design（最小前端）

### 实现要点
- 明确后端框架与目录结构后再落地路由与依赖
- 认证与权限采用强哈希算法（替换文档中的 MD5 方案）
- 锁定与释放使用 text_locks 的 released_at 作为释放标识
- 校验接口先实现最小规则集合，避免阻塞主流程

## 架构决策 ADR
### ADR-002: 后端框架选择
**上下文:** 当前仅有迁移脚本，缺少后端框架与基础工程结构。
**决策:** 选择 FastAPI。
**理由:** FastAPI 类型提示完善、文档自带、适合快速构建 API。
**替代方案:** Flask → 拒绝原因: 需额外补齐文档与类型约束。
**影响:** 目录结构、依赖管理与测试方式随框架变化。

## API设计
### [POST] /auth/login
- **请求:** { username, password }
- **响应:** { user, roles, permissions, token }

### [GET] /texts
- **请求:** fid/part/status/keyword/page/page_size
- **响应:** { items, total, page, page_size }

### [GET] /texts/{id}
- **响应:** { text, claims, locks }

### [POST] /claims
- **请求:** { text_id }
- **响应:** { claim_id }

### [POST] /locks
- **请求:** { text_id }
- **响应:** { lock_id, expires_at }

### [DELETE] /locks/{id}
- **响应:** { released_at }

### [GET] /changes?text_id=...
- **响应:** { items }

### [GET] /dictionary
- **请求:** keyword/category/is_active/page/page_size
- **响应:** { items, total }

### [POST] /dictionary
- **请求:** { term_key, term_value, category }

### [PUT] /dictionary/{id}
- **请求:** { term_key, term_value, category, is_active }

### [POST] /validate
- **请求:** { text_id, translated_text }
- **响应:** { valid, errors }

## 数据模型
```sql
-- 新增迁移：为 text_locks 增加 released_at（如未初始化可改 001_init.sql）
ALTER TABLE text_locks ADD COLUMN released_at TIMESTAMP;
```

## 安全与性能
- **安全:** 密码哈希采用 bcrypt/argon2；接口权限校验最小化开放面
- **性能:** 列表与检索使用现有索引；锁定查询使用局部唯一索引

## 测试与部署
- **测试:** 锁定冲突、关键词检索、词典筛选、校验失败路径
- **部署:** 先本地/测试库验证迁移与接口，再部署
