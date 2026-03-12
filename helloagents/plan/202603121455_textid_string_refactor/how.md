# 技术设计: textId 字符串化与全链路修正

## 技术方案
### 核心技术
- 后端: FastAPI + MySQL
- 前端: React + Ant Design + ProTable
- 工具链: Python + openpyxl + SQLite + MySQL SQL 脚本

### 实现要点
- 将所有“业务 textId”统一定义为 `string`/`VARCHAR`，与内部主键 `id`（bigint）严格区分。
- 重写协议段解析规则：三类格式都必须返回完整字符串 textId，而不是 `int(matched.group("textId"))`。
- 在修改字段类型后，新增一条“旧库错误值 → 正确值”的映射生成链路：从原始 SQLite/XLSX 解析出正确 textId，再与现库错误数据按 `fid` + 可验证辅助条件（如 sourceText/sourceTextHash/part）匹配，输出供全局 update 使用的对照表。
- 后端 `/texts`、`/texts/download`、`/texts/children`、`/texts/by-textid` 的 `textId` 参数改为字符串；SQL 保持按 `tm."textId" = %s` 精确匹配。
- 前端 `QueryParams`、列表筛选、详情编辑路由入参与 mock 数据统一改为字符串 textId。
- 版本迭代 Step4/5/6/7 与 map 表改为字符串 textId，并重新校验 `(fid, textId, part)` join 行为。
- 对约 80 万行数据的索引策略做专项评估：保留高价值精确匹配索引，避免无意义冗余索引。

## 架构决策 ADR
### ADR-001: textId 作为业务字符串键，内部 id 保持数值主键
**上下文:** 当前系统混淆了内部主键 `id` 与业务标识 `textId`。真实业务 textId 来自协议头，可能包含 `:::` 和范围段，不满足数值型假设。
**决策:** 将 `text_main.textId` 明确定义为字符串业务键；所有对外查询、导入、版本迭代按字符串 textId 工作；内部关联仍通过 `text_main.id`、`text_changes.textId`、`text_claims.textId`、`text_locks.textId` 维持数值外键。
**理由:** 这样可以最小化对关联表的冲击，同时修正真正错误的字段建模。
**替代方案:**
- 保持 bigint，只在工具层拼接虚拟 textId → 会继续丢失真实业务键，直接错误
- 新增 `rawTextId` 字段并保留旧 `textId` → 会长期并存两个业务键，前后端复杂度和错用风险极高
**影响:** 需要同步修改数据库 schema、接口参数、前端类型、正则解析与版本迭代 SQL。

### ADR-002: 旧数据修复采用“字段改型 + 映射对照 + 全局更新”
**上下文:** 用户已经明确旧数据不走整库重导，而是先把 `text_main.textId` 改成字符串，再拿到“错误 fid+textId → 正确 fid+textId”对照结果后执行全局 update。
**决策:** 先完成字段类型改造，再从原始源数据解析出正确 textId，生成可审计的对照结果；映射结果至少包含 `fid`、错误 `textId`、正确 `textId`，必要时补充 `sourceTextHash/part` 等辅助校验列。
**理由:** 这样既符合当前修复路径，也保留了人工校验与分批更新的控制权，避免直接在解析阶段做不可回滚的批量修改。
**替代方案:**
- 整库重导 → 更干净，但不符合当前用户选择的修复路径
- 直接在线 UPDATE 不产出对照表 → 风险高，无法审计和回滚
**影响:** 实施阶段必须新增映射生成脚本/SQL，并输出可直接用于全局 update 的结果集。

### ADR-003: 80 万行场景下保留精确匹配导向索引
**上下文:** `textId` 从 `BIGINT` 改成 `VARCHAR` 后，索引体积会增加，但系统存在按 `fid+textId` 精确查询、列表按 `fid`/`status`/`uptTime` 过滤、版本迭代按业务键 join 的高频场景。
**决策:** 保留 `uq_text_main_fid_text_id(fid, textId)` 与 `idx_text_main_text_id(textId)`；继续保留 `idx_text_main_fid_part(fid, part)`、`idx_text_main_status(status)`、`idx_text_main_upt_time(uptTime)`。
**理由:**
- `uq_text_main_fid_text_id` 是详情定位、去重约束、版本修复映射的核心索引，不能删。
- `idx_text_main_text_id` 对跨 fid 排查、错误数据筛查、映射生成与运维 SQL 有价值，在 80 万行规模下仍值得保留。
- `idx_text_main_fid_part` 继续支撑按 fid 聚合/展开与版本迭代相关排序。
**替代方案:**
- 仅保留组合索引、删除 `textId` 单列索引 → 会让按 textId 单条件排查与修复 SQL 退化
- 额外新增更长的覆盖索引 `(fid,textId,part)` 到主表 → 当前唯一约束已按 `(fid,textId)` 设计，先不盲目扩索引，待 explain 再定
**影响:** 实施后需要通过 `EXPLAIN`/执行统计确认索引选择正常；若发现单列 `textId` 命中率低，再考虑后续收缩。

## API设计
### [GET] /texts
- **请求:** `fid?: string`, `textId?: string`, `status?: number`, `sourceKeyword?: string`, `translatedKeyword?: string`, `updatedFrom?: string`, `updatedTo?: string`, `claimer?: string`, `claimed?: boolean`, `page`, `pageSize`
- **响应:** 列表结构不变，但 `textId` 字段语义改为字符串

### [GET] /texts/children
- **请求:** `fid: string`, `textId?: string`, `sourceKeyword?: string`, `translatedKeyword?: string`, `page`, `pageSize`
- **响应:** 指定 fid 下按字符串 textId 过滤的子列表
- **校验:** 同一 fid 下若存在重复 `(fid,textId)` 仍按原规则视业务冲突处理

### [GET] /texts/by-textid
- **请求:** `fid: string`, `textId: string`
- **响应:** 唯一记录 + 内部 id
- **校验:** 0 条返回 404；多条返回 409

### [GET] /texts/download
- **请求:** 增加 `textId?: string`
- **响应:** 导出结果中的 `TextId` 按字符串原样写入

### [POST] /texts/upload
- **请求:** 模板中的 `TextId` 列按字符串读取并与数据库精确比对
- **响应:** 仍返回 `updatedCount`

## 数据模型
```sql
-- 主表字段类型改造
ALTER TABLE text_main
  MODIFY COLUMN `textId` VARCHAR(255) NOT NULL COMMENT '文本标识（业务字符串）';

-- 主表索引策略
DROP INDEX idx_text_main_text_id ON text_main;
DROP INDEX uq_text_main_fid_text_id ON text_main;

CREATE UNIQUE INDEX uq_text_main_fid_text_id ON text_main(fid, `textId`);
CREATE INDEX idx_text_main_text_id ON text_main(`textId`);

-- 主表其余索引继续保留
-- idx_text_main_fid(fid)
-- idx_text_main_fid_part(fid, part)
-- idx_text_main_status(status)
-- idx_text_main_upt_time(uptTime)

-- 版本迭代 map 表同步改型
CREATE TABLE text_id_map_xxx (
  `oldId` BIGINT NOT NULL,
  `newId` BIGINT NOT NULL,
  fid VARCHAR(64) NOT NULL,
  `textId` VARCHAR(255) NOT NULL,
  part INT NOT NULL,
  `sourceTextHash` VARCHAR(64) NOT NULL,
  PRIMARY KEY (`oldId`),
  UNIQUE KEY uq_map_new_id (`newId`),
  UNIQUE KEY uq_map_text_key (fid, `textId`)
);

-- 错误值 -> 正确值 对照结果（建议落临时表或导出 CSV）
CREATE TABLE text_id_fix_map (
  fid VARCHAR(64) NOT NULL,
  wrongTextId VARCHAR(255) NOT NULL,
  correctTextId VARCHAR(255) NOT NULL,
  sourceTextHash VARCHAR(64) NULL,
  part INT NULL,
  PRIMARY KEY (fid, wrongTextId, correctTextId)
);
```

## 安全与性能
- **安全:** 禁止用猜测式规则从旧 bigint 反推复合 textId；任何不可恢复数据必须阻断并显式报错。
- **安全:** 前后端输入只做边界校验，不做 silent fallback；空字符串视为未传，非法格式由解析/校验链路直接报错。
- **性能:** `textId` 改为 `VARCHAR` 后，保留 `idx_text_main_text_id` 与 `uq_text_main_fid_text_id`，避免精确查询退化；Step5/6 仍依赖 `(fid,textId,part)` 复合键。

## 测试与部署
- **测试:**
  - 工具层：协议段解析用例覆盖 `::::::`、`:::num:::`、`:::range:::`，并断言返回完整字符串 textId
  - 后端：`/texts`、`/texts/download`、`/texts/children`、`/texts/by-textid` 对复合 textId 的查询与导出
  - 前端：列表筛选可提交并回显字符串 textId
  - 版本迭代：Step4/5/6 对复合 textId 生成、比对、映射正确
- **部署:**
  1. 先执行旧数据可恢复性审计
  2. 可恢复 → 产出正式迁移/重导脚本并回灌
  3. 不可恢复 → 明确废弃旧库，按原始 SQLite/XLSX 全量重建
  4. 重建后再切换前后端与工具链到字符串 textId 语义
