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
| passwordHash | varchar | 加盐 MD5 后的密码 |
| passwordSalt | varchar | 盐值 |
| isGuest | boolean | 是否游客 |
| createdAt | timestamp | 创建时间 |
| updatedAt | timestamp | 更新时间 |

### roles
| 字段 | 类型 | 说明 |
|------|------|------|
| id | bigint | 主键 |
| name | varchar | 角色名（游客/汉化人员/管理员） |
| description | varchar | 角色描述 |

### user_roles
| 字段 | 类型 | 说明 |
|------|------|------|
| userId | bigint | 用户ID |
| roleId | bigint | 角色ID |

### permissions
| 字段 | 类型 | 说明 |
|------|------|------|
| id | bigint | 主键 |
| permKey | varchar | 权限标识 |
| description | varchar | 权限描述 |

### role_permissions
| 字段 | 类型 | 说明 |
|------|------|------|
| roleId | bigint | 角色ID |
| permId | bigint | 权限ID |

---

## 主文本与翻译

### text_main
| 字段 | 类型 | 说明 |
|------|------|------|
| id | bigint | 主键 |
| fid | varchar | 文件标识 |
| textId | bigint | 文本标识 |
| part | int | 分段顺序 |
| sourceText | text | 原文（允许为空） |
| translatedText | text | 译文 |
| status | smallint | 状态（1=新增/2=修改/3=已完成） |
| isClaimed | boolean | 是否已认领（未认领/已认领） |
| editCount | int | 变更次数（默认0） |
| updatedAt | timestamp | 最近更新时间 |
| createdAt | timestamp | 创建时间 |

#### 索引与性能
- 查询索引: fid, (fid, part), textId, (fid, textId)
- 部分索引: (fid) WHERE part=1
- 筛选索引: status, updatedAt
- 关键词检索: sourceText/translatedText 使用 GIN + pg_trgm

### text_claims
| 字段 | 类型 | 说明 |
|------|------|------|
| id | bigint | 主键 |
| textId | bigint | 关联 text_main |
| userId | bigint | 认领人 |
| claimedAt | timestamp | 认领时间 |

### text_locks
| 字段 | 类型 | 说明 |
|------|------|------|
| id | bigint | 主键 |
| textId | bigint | 关联 text_main |
| userId | bigint | 锁定人 |
| lockedAt | timestamp | 锁定时间 |
| expiresAt | timestamp | 过期时间 |
| releasedAt | timestamp | 释放时间 |

### text_changes
| 字段 | 类型 | 说明 |
|------|------|------|
| id | bigint | 主键 |
| textId | bigint | 关联 text_main |
| userId | bigint | 操作者 |
| beforeText | text | 变更前文本 |
| afterText | text | 变更后文本 |
| reason | varchar | 变更原因 |
| changedAt | timestamp | 变更时间 |

---

## 词典

### dictionary_entries
| 字段 | 类型 | 说明 |
|------|------|------|
| id | bigint | 主键 |
| termKey | varchar | 词条 key（用于原文高亮） |
| termValue | varchar | 词条 value（用于译文高亮） |
| category | varchar | 分类 |
| isActive | boolean | 是否启用 |
| createdAt | timestamp | 创建时间 |
| updatedAt | timestamp | 更新时间 |
