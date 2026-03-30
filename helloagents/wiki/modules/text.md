# 文本任务与翻译

## 目的
管理主文本、认领任务、翻译编辑与锁定。

## 模块概述
- **职责:** 主文本列表、筛选分页、认领、锁定、翻译保存、变更历史
- **状态:** 🧪实现中
- **最后更新:** 2026-03-29

## 规范

### 需求: 主文本维护与认领
**模块:** 文本任务与翻译
支持按 fid + textId 认领任务，支持多人认领但单人编辑锁定。

#### 场景: 进入翻译页锁定
- 用户从列表进入翻译页
- 系统锁定该文本，避免多人同时编辑

## API接口
### [GET] /texts
**描述:** 父级列表与筛选（仅 part=1）
**输入:** fid/状态/原文关键字/汉化关键字/更新时间范围/认领人/是否认领/分页
**输出:** 父级主文本列表

### [GET] /texts/children
**描述:** 子列表（按 fid 展开）
**输入:** fid（必填）/textId（可选，字符串精确匹配）/sourceKeyword（可选）/translatedKeyword（可选）/分页（默认排除 part=1）
**输出:** 指定 fid 的拆分列表

### [GET] /texts/by-textid
**描述:** fid + textId 精确查询
**输入:** fid/textId
**输出:** 单条主文本详情

### [POST] /locks
**描述:** 锁定文本
**输入:** `id`（text_main.id 内部主键，非业务 textId）
**输出:** 锁定结果

### [PUT] /texts/{textId}/translate
**描述:** 保存译文并写入变更记录
**输入:** translatedText, reason
**输出:** 更新结果

### [GET] /texts/template
**描述:** 下载离线翻译模板（xlsx，仅表头）
**输入:** 无
**输出:** 固定列顺序的模板文件（编号/FID/TextId/Part/原文/译文/状态）

### [GET] /texts/download
**描述:** 根据筛选条件导出文本结果
**输入:** fid/status/sourceKeyword/translatedKeyword/updatedFrom/updatedTo/claimer/claimed
**输出:** 匹配筛选条件的 xlsx 数据文件

### [GET] /texts/download-package
**描述:** 下载汉化包，按 fid 合并分段并还原协议格式
**输入:** 复用 `/texts/download` 的筛选参数
**输出:** 适配汉化流程的 xlsx 数据文件

### [POST] /texts/upload
**描述:** 上传离线翻译结果并批量更新
**输入:** `fileName`（query）、可选 `reason`（query）、xlsx 二进制 body
**输出:** 更新数量 `updatedCount`

### [DELETE] /claims/{claimId}
**描述:** 释放认领
**输入:** claimId
**输出:** 释放结果

## 数据模型
### text_main
| 字段 | 类型 | 说明 |
|------|------|------|
| id | bigint | 主键（内部自增 ID，供外键关联） |
| fid | varchar | 文件标识 |
| textId | varchar(255) | 业务文本标识（字符串，支持复合格式） |
| part | int | 分段顺序 |
| sourceText | text | 原文（允许为空） |
| translatedText | text | 译文 |
| status | smallint | 状态（1=新增/2=修改/3=已完成） |
| isClaimed | boolean | 是否已认领 |
| editCount | int | 变更次数（默认0） |

### text_changes
| 字段 | 类型 | 说明 |
|------|------|------|
| id | bigint | 主键 |
| textId | bigint | 关联 text_main.id（内部主键） |
| beforeText | text | 变更前 |
| afterText | text | 变更后 |

## 依赖
- 用户与权限
- 词典管理
- 文本校验

## 实施说明
- 列表与详情接口已落地（/texts/parents, /texts/children, /texts/by-textid）
- 认领与锁定接口已落地（/claims, /locks），释放使用 text_locks.releasedAt 标记
- 变更历史查询已落地（/changes），查询参数为 `id`（text_main.id）
- **textId 字段类型**：`text_main.textId` 已从 BIGINT 改为 VARCHAR(255)，支持复合格式（如 `126853056:::337429-296068`）；`text_claims/locks/changes.textId` 保持 BIGINT，关联 `text_main.id` 内部主键
- **/claims、/locks 请求体**：字段名从 `textId` 改为 `id`（明确为内部主键，非业务 textId）
- 主文本列表补充原文/译文/编辑次数显示，长文本使用截断+悬浮展示
- 列表接口对 sourceText/translatedText 超长内容截断（配置 `text_list.max_text_length`）
- 数据库编码需为 UTF8，以兼容稀有符号与带音节字符
- 提供 xlsx 批量导入脚本 `tools/valid_format/xlsx_to_insert.py`（按行范围与分块生成 INSERT）
- 新增模板化下载/上传闭环：导出按筛选条件执行；上传按 `编号` 定位并强校验 `FID/TextId/Part`，失败即整批回滚，成功后统一写入 `text_changes`
- 导出链路支持大数据量安全导出：服务端流式查询、分批写入、临时文件回传，避免高峰内存占用
- 文本列表中的“导出”和“下载汉化包”按钮均提供下载中加载态与阶段文案，避免用户误判为未触发

## 变更历史
- 2026-01-31：列表字段补全与长文本展示
- 2026-02-08：textId 拆分、父/子列表与 fid+textId 查询
- 2026-02-11：数据库与 API 字段统一 camelCase
- 2026-03-01：新增文本模板下载/上传（离线翻译回传）
- 2026-03-12：text_main.textId 从 BIGINT 改为 VARCHAR(255)，支持复合协议格式；/claims、/locks 请求体字段名从 textId 改为 id；/changes 查询参数从 textId 改为 id
- 2026-03-29：导出按钮补齐下载进度反馈，并补全文档中的汉化包下载接口说明
