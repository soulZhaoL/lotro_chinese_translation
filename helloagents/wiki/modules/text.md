# 文本任务与翻译

## 目的
管理主文本、认领任务、翻译编辑与锁定。

## 模块概述
- **职责:** 主文本列表、筛选分页、认领、锁定、翻译保存、变更历史
- **状态:** 🧪实现中
- **最后更新:** 2026-01-31

## 规范

### 需求: 主文本维护与认领
**模块:** 文本任务与翻译
支持按 fid + part 认领任务，支持多人认领但单人编辑锁定。

#### 场景: 进入翻译页锁定
- 用户从列表进入翻译页
- 系统锁定该文本，避免多人同时编辑

## API接口
### [GET] /texts
**描述:** 列表与筛选
**输入:** fid/part/状态/原文关键字/汉化关键字/更新时间范围/认领人/是否认领/分页
**输出:** 主文本列表

### [POST] /locks
**描述:** 锁定文本
**输入:** text_id
**输出:** 锁定结果

### [PUT] /texts/{id}/translate
**描述:** 保存译文并写入变更记录
**输入:** translated_text, reason
**输出:** 更新结果

### [DELETE] /claims/{id}
**描述:** 释放认领
**输入:** claim_id
**输出:** 释放结果

## 数据模型
### text_main
| 字段 | 类型 | 说明 |
|------|------|------|
| id | bigint | 主键 |
| fid | varchar | 文件标识 |
| part | varchar | 分段标识 |
| source_text | text | 原文（允许为空） |
| translated_text | text | 译文 |
| status | smallint | 状态（1=新增/2=修改/3=已完成） |
| is_claimed | boolean | 是否已认领 |
| edit_count | int | 变更次数（默认0） |

### text_changes
| 字段 | 类型 | 说明 |
|------|------|------|
| id | bigint | 主键 |
| text_id | bigint | 关联主文本 |
| before_text | text | 变更前 |
| after_text | text | 变更后 |

## 依赖
- 用户与权限
- 词典管理
- 文本校验

## 实施说明
- 列表与详情接口已落地（/texts）
- 认领与锁定接口已落地（/claims, /locks），释放使用 text_locks.released_at 标记
- 变更历史查询已落地（/changes）
- 主文本列表补充原文/译文/编辑次数显示，长文本使用截断+悬浮展示
- 列表接口对 source_text/translated_text 超长内容截断（配置 `text_list.max_text_length`）
- 数据库编码需为 UTF8，以兼容稀有符号与带音节字符
- 提供 xlsx 批量导入脚本 `tools/xlsx_to_insert.py`（按行范围与分块生成 INSERT） 

## 变更历史
- 2026-01-31：列表字段补全与长文本展示
