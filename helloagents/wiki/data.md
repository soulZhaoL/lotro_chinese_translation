# 数据模型

## 概述
本文件描述计划中的核心数据表，最终以实现为准。

---

## 用户与权限

### users
| 字段 | 类型 | 说明 |
|------|------|------|
| id | bigint | 主键 |
| username | varchar | 用户名 |
| password_hash | varchar | 加盐 MD5 后的密码 |
| password_salt | varchar | 盐值 |
| is_guest | boolean | 是否游客 |
| created_at | timestamp | 创建时间 |
| updated_at | timestamp | 更新时间 |

### roles
| 字段 | 类型 | 说明 |
|------|------|------|
| id | bigint | 主键 |
| name | varchar | 角色名（游客/汉化人员/管理员） |
| description | varchar | 角色描述 |

### user_roles
| 字段 | 类型 | 说明 |
|------|------|------|
| user_id | bigint | 用户ID |
| role_id | bigint | 角色ID |

### permissions
| 字段 | 类型 | 说明 |
|------|------|------|
| id | bigint | 主键 |
| perm_key | varchar | 权限标识 |
| description | varchar | 权限描述 |

### role_permissions
| 字段 | 类型 | 说明 |
|------|------|------|
| role_id | bigint | 角色ID |
| perm_id | bigint | 权限ID |

---

## 主文本与翻译

### text_main
| 字段 | 类型 | 说明 |
|------|------|------|
| id | bigint | 主键 |
| fid | varchar | 文件标识 |
| part | varchar | 分段标识 |
| source_text | text | 原文 |
| translated_text | text | 译文 |
| status | varchar | 状态（待认领/已认领） |
| edit_count | int | 变更次数 |
| updated_at | timestamp | 最近更新时间 |
| created_at | timestamp | 创建时间 |

### text_claims
| 字段 | 类型 | 说明 |
|------|------|------|
| id | bigint | 主键 |
| text_id | bigint | 关联 text_main |
| user_id | bigint | 认领人 |
| claimed_at | timestamp | 认领时间 |

### text_locks
| 字段 | 类型 | 说明 |
|------|------|------|
| id | bigint | 主键 |
| text_id | bigint | 关联 text_main |
| user_id | bigint | 锁定人 |
| locked_at | timestamp | 锁定时间 |
| expires_at | timestamp | 过期时间 |

### text_changes
| 字段 | 类型 | 说明 |
|------|------|------|
| id | bigint | 主键 |
| text_id | bigint | 关联 text_main |
| user_id | bigint | 操作者 |
| before_text | text | 变更前文本 |
| after_text | text | 变更后文本 |
| reason | varchar | 变更原因 |
| changed_at | timestamp | 变更时间 |

---

## 词典

### dictionary_entries
| 字段 | 类型 | 说明 |
|------|------|------|
| id | bigint | 主键 |
| term_key | varchar | 词条 key（用于原文高亮） |
| term_value | varchar | 词条 value（用于译文高亮） |
| category | varchar | 分类 |
| is_active | boolean | 是否启用 |
| created_at | timestamp | 创建时间 |
| updated_at | timestamp | 更新时间 |
