# API 手册

## 概述
本文件描述计划中的核心接口，最终以实现为准。当前仅完成数据库迁移脚本，接口仍处于规划阶段。

## 认证方式
- 登录获取签名 token（HMAC），后续请求通过 `Authorization: Bearer <token>` 传递

---

## 接口列表

### 认证

#### [POST] /auth/login
**描述:** 用户登录

**请求参数:**
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| username | string | 是 | 用户名 |
| password | string | 是 | 明文密码（服务端按配置的 hash_algorithm 校验） |

**响应:**
- 登录成功信息与用户角色、权限、token
```json
{
  "user": { "id": 1, "username": "tester", "is_guest": false },
  "roles": ["translator"],
  "permissions": ["text.read"],
  "token": "..."
}
```

**错误码:**
- 401 用户名或密码错误

---

### 主文本与任务

#### [GET] /texts
**描述:** 获取主文本列表（支持筛选与分页）

**请求参数:** fid/part/status/keyword/page/page_size

**响应:**
```json
{
  "items": [{ "id": 1, "fid": "file_a", "part": "p1", "status": "待认领" }],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

#### [GET] /texts/{id}
**描述:** 获取主文本详情

**响应:**
```json
{
  "text": { "id": 1, "fid": "file_a", "part": "p1" },
  "claims": [],
  "locks": []
}
```

#### [POST] /claims
**描述:** 认领任务（fid + part）

**响应:**
```json
{ "claim_id": 1 }
```

#### [POST] /locks
**描述:** 进入翻译页锁定文本

**响应:**
```json
{ "lock_id": 1, "expires_at": "2026-01-30T12:00:00Z" }
```

#### [DELETE] /locks/{id}
**描述:** 释放锁定

**响应:**
```json
{ "released_at": "2026-01-30T11:30:00Z" }
```

---

### 变更历史

#### [GET] /changes?text_id=...
**描述:** 获取文本变更历史

**响应:**
```json
{ "items": [{ "id": 1, "text_id": 1, "before_text": "...", "after_text": "..." }] }
```

---

### 词典管理

#### [GET] /dictionary
**描述:** 获取词典列表

**响应:**
```json
{
  "items": [{ "id": 1, "term_key": "orc", "term_value": "兽人" }],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

#### [POST] /dictionary
**描述:** 新增词条

**响应:**
```json
{ "id": 1 }
```

#### [PUT] /dictionary/{id}
**描述:** 更新词条

**响应:**
```json
{ "id": 1 }
```

---

### 文本校验

#### [POST] /validate
**描述:** 校验翻译文本格式

**响应:**
```json
{ "valid": true, "errors": [] }
```
