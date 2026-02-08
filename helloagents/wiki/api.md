# API 手册

## 概述
本文件描述计划中的核心接口，最终以实现为准。

### 统一响应结构
所有接口均返回以下结构：
```json
{
  "success": true,
  "statusCode": 200,
  "code": "0000",
  "message": "操作成功",
  "data": {}
}
```

当 `code != "0000"` 时表示异常，前端应直接展示 `message`。

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

#### [GET] /texts/parents
**描述:** 获取父级主文本列表（仅 part=1，支持筛选与分页）

**请求参数:** fid/status(1=新增/2=修改/3=已完成)/source_keyword/translated_keyword/updated_from/updated_to/claimer/claimed/page/page_size

**响应:**
```json
{
  "items": [
    {
      "id": 1,
      "fid": "file_a",
      "text_id": 10001,
      "part": 1,
      "status": 1,
      "claim_id": 10,
      "claimed_by": "tester",
      "claimed_at": "2026-01-30T10:00:00Z",
      "is_claimed": true
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

#### [GET] /texts/children
**描述:** 获取指定 fid 的子列表（默认排除 part=1）

**请求参数:** fid（必填）/text_id（可选）/source_keyword（可选）/translated_keyword（可选）/page/page_size

**响应:** 同父列表结构，按 part 升序

#### [GET] /texts/by-textid
**描述:** fid + textId 精确查询

**请求参数:** fid/text_id

**响应:**
```json
{
  "text": { "id": 1, "fid": "file_a", "text_id": 10001, "part": 1 },
  "claims": [],
  "locks": []
}
```

#### [GET] /texts/{id}
**描述:** 获取主文本详情（内部 ID）

**响应:**
```json
{
  "text": { "id": 1, "fid": "file_a", "text_id": 10001, "part": 1 },
  "claims": [],
  "locks": []
}
```

#### [POST] /claims
**描述:** 认领任务（text_main.id）

**响应:**
```json
{ "claim_id": 1 }
```

#### [DELETE] /claims/{id}
**描述:** 释放认领

**响应:**
```json
{ "id": 1 }
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

**请求参数:**
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| keyword | string | 否 | 兼容关键字（原文/译文模糊匹配） |
| term_key | string | 否 | 原文模糊匹配 |
| term_value | string | 否 | 译文模糊匹配 |
| category | string | 否 | 分类 |
| is_active | boolean | 否 | 是否启用 |
| page | int | 否 | 页码 |
| page_size | int | 否 | 每页数量 |

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

#### [PUT] /texts/{id}/translate
**描述:** 保存译文并写入变更记录

**请求:**
```json
{ "translated_text": "...", "reason": "修正说明", "is_completed": true }
```

**响应:**
```json
{ "id": 1 }
```

---

### 健康检查

#### [GET] /health
**描述:** 服务健康检查

**响应:**
```json
{ "status": "ok" }
```
