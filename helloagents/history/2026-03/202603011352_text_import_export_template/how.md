# 技术设计: 文本模板下载/上传

## 技术方案

### 后端接口设计
1. `GET /texts/download`
- 根据筛选条件（fid/status/sourceKeyword/translatedKeyword/updatedFrom/updatedTo/claimer/claimed）导出 xlsx。
- 表头固定为: `编号`、`FID`、`TextId`、`Part`、`原文`、`译文`、`状态`。
- 支持大数据量导出：流式 DB 游标 + 分批 `fetchmany` + `openpyxl write_only` + 临时文件回传。

2. `GET /texts/template`
- 仅下载模板表头，供离线编辑起始文件使用。

3. `POST /texts/upload`
- 使用二进制请求体上传 xlsx 文件（`Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`）。
- 通过 query 参数传递 `fileName`（必填）与 `reason`（可选）。
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
1. 将“导出筛选结果/下载模板/上传结果”统一放在筛选区域操作栏（搜索按钮旁）。
2. “导出筛选结果”读取当前筛选参数后发起下载。
3. “上传结果”按钮配合隐藏文件选择器，限制 `.xlsx`。
4. 上传成功后提示并刷新列表；失败展示后端错误信息。
5. 上传请求使用 `fetch` 发送二进制 body，避免 `multipart` 依赖导致后端启动前置校验失败。

## 安全与性能
- 安全:
  - 强模板校验避免列错位写入。
  - 主键+业务键双重一致性校验防止误更新。
- 性能:
  - 导出采用流式读取和分批写入，规避百万级数据的内存峰值风险。
  - 通过配置约束最大导出量与批次大小，防止单次导出拖垮服务。

## 测试与验证
1. 模板下载测试: 校验 xlsx 表头。
2. 筛选导出测试: 校验筛选条件生效且数据正确。
2. 上传成功测试: 校验 text_main 变更与 text_changes 记录。
3. 上传失败测试: 编号/FID/TextId/Part 不匹配时报错且数据不变。
4. 运行文本模块相关 pytest 回归。
5. 增加 pytest 分层：纯逻辑测试默认可运行；数据库集成测试通过 `--run-db-tests` 显式启用。
