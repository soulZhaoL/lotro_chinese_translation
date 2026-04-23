# 词典管理

## 目的
维护专有名词词典并在翻译时提供高亮与数量提示。

## 模块概述
- **职责:** 词条维护、原文 key 高亮、译文 value 高亮、数量匹配提示
- **状态:** 🧪实现中
- **最后更新:** 2026-02-11

## 规范

### 需求: 词典高亮与数量提示
**模块:** 词典管理
原文中存在 n 个 key，译文中必须出现 n 个对应 value，否则提示。

#### 场景: 翻译时提示
- 系统从原文提取词典 key 匹配次数
- 翻译内容中统计 value 次数
- 不一致时给出提示

## API接口
### [GET] /dictionary
**描述:** 获取词典列表
**输入:** 分页/筛选
**输出:** 词典条目

### [GET] /dictionary/template
**描述:** 下载词典导入模板
**输入:** 无
**输出:** xlsx 文件，表头固定为 `原文 key/译文 value/分类/备注`

### [GET] /dictionary/download
**描述:** 根据筛选条件导出词典
**输入:** 复用 `/dictionary` 的筛选参数
**输出:** xlsx 文件，列顺序与模板一致

### [POST] /dictionary/upload
**描述:** 批量导入词典
**输入:** `fileName`（query）+ xlsx 二进制 body
**输出:** `createdCount`、`updatedCount`

## 数据模型
### dictionary_entries
| 字段 | 类型 | 说明 |
|------|------|------|
| id | bigint | 主键 |
| termKey | varchar | 原文 key |
| termValue | varchar | 译文 value |
| category | varchar | 分类 |
| remark | varchar | 备注 |
| isActive | boolean | 是否启用 |
| lastModifiedBy | bigint | 最后修改人 |

## 依赖
- 文本任务与翻译

## 实施说明
- 词典列表已升级为 ProTable 风格，与文本管理的搜索区和按钮布局保持一致
- 词典 CRUD 与筛选接口已落地（/dictionary）
- 前端分类使用枚举映射（如 skill -> 技能），筛选使用下拉选择框
- 查询条件拆分为原文/译文，并提供新增/修改弹窗表单
- 支持词典模板下载、筛选导出与批量导入
- 导入按 `termKey` 覆盖或新增，严格校验表头并整批事务提交
- 列表补充备注、修改人字段显示

## 变更历史
- 2026-01-31：分类枚举映射与筛选下拉
- 2026-01-31：筛选字段拆分与新增弹窗
- 2026-02-11：词典接口字段统一为 camelCase
- 2026-04-17：词典页面升级为 ProTable 风格，新增修改/导入/导出/模板下载、备注与修改人展示
