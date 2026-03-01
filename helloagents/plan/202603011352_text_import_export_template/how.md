# 技术设计: 文本模板下载/上传

## 技术方案

### 后端接口设计
1. `GET /texts/download`
- 查询 `text_main` 并按 `id ASC` 导出 xlsx。
- 表头固定为: `编号`、`FID`、`TextId`、`Part`、`原文`、`译文`、`状态`。
- 以附件形式返回文件，供翻译人员线下编辑。

2. `POST /texts/upload`
- 使用 `multipart/form-data` 上传 xlsx 文件。
- 校验项:
  - 文件扩展名必须为 `.xlsx`
  - 工作表存在且表头严格匹配模板列顺序
  - 每行必填字段: `编号/FID/TextId/Part/状态`
  - `状态` 必须为 `1/2/3` 或中文枚举（新增/修改/已完成）
- 业务校验:
  - 用 `编号` 查询 `text_main.id`
  - 比对 `FID/TextId/Part` 是否与数据库一致
  - 任一不一致立即抛错
- 更新行为:
  - 覆盖 `translatedText`、`status`
  - `editCount = editCount + 1`
  - `uptTime = NOW()`
  - 写入 `text_changes`（`beforeText`/`afterText`/`reason`）

### 原子性策略
- 上传接口在单事务内执行:
1. 先解析并校验全部行。
2. 校验全通过后再批量更新。
3. 任意异常直接回滚，禁止部分成功。

### 前端交互设计
1. 文本列表页新增“下载模板”按钮，调用下载接口并触发浏览器保存。
2. 新增“上传结果”按钮与隐藏文件选择器，限制 `.xlsx`。
3. 上传成功后提示并刷新列表；失败展示后端错误信息。
4. 调整 `apiFetch`，`FormData` 请求不自动设置 `Content-Type: application/json`。

## 安全与性能
- 安全:
  - 强模板校验避免列错位写入。
  - 主键+业务键双重一致性校验防止误更新。
- 性能:
  - 目标场景为翻译批量回传，优先保证数据正确性而非极限吞吐。
  - 若后续数据量明显增长，可新增上传行数配置并分页批处理。

## 测试与验证
1. 下载接口测试: 校验 xlsx 表头与示例行。
2. 上传成功测试: 校验 text_main 变更与 text_changes 记录。
3. 上传失败测试: 编号/FID/TextId/Part 不匹配时报错且数据不变。
4. 运行文本模块相关 pytest 回归。
