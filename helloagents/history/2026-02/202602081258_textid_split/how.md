# 技术设计: textId拆分与嵌套列表

## 技术方案
### 核心技术
- 后端: FastAPI + PostgreSQL
- 前端: React + Ant Design + ProTable

### 实现要点
- 数据模型新增 `text_id` (BIGINT)，`part` 改为顺序编号（建议 INTEGER），移除 fid+part 唯一索引，新增按 fid/part/text_id 的查询索引与 part=1 的部分索引。
- 拆分父/子列表专用接口：父列表仅返回 part=1 记录；子列表必须携带 fid，支持 textId 查询与分页。
- 详情/编辑新增 fid+textId 查询接口，返回唯一记录与内部 id；若发现重复 textId 直接 409。
- 前端采用嵌套表格：外层分页、内层分页与 textId 过滤；点击详情/编辑进入时保存父/子表状态，返回时恢复。

## 架构决策 ADR
### ADR-001: 单表增强 + 双接口（已采纳）
**上下文:** 需要在不引入新汇总表的前提下支持父/子列表与 textId 精确查询，同时避免接口混用带来的性能问题。  
**决策:** 保持 `text_main` 单表，新增 `text_id` 与索引，增加父/子列表专用接口。  
**理由:** 改动最小、数据一致性更易维护、接口职责清晰。  
**替代方案:**  
- 双表（fid 汇总表 + 明细表） → 需要同步维护，增加迁移与一致性成本  
- 视图/物化视图驱动父列表 → 需要刷新策略，增加运维复杂度  
**影响:** API 层需要明确区分父/子列表访问路径，前端需配合新交互方式。

## API 设计
### [GET] /texts/parents
- **请求:** fid/status/source_keyword/translated_keyword/updated_from/updated_to/claimer/claimed/page/page_size
- **响应:** 仅 part=1 的列表结果，包含 text_id

### [GET] /texts/children
- **请求:** fid(必填)/text_id(可选)/page/page_size
- **响应:** 指定 fid 的拆分列表，按 part 升序，包含 text_id
- **校验:** 若发现同 fid 下 text_id 重复，返回 409 并提示重复项

### [GET] /texts/by-textid
- **请求:** fid(必填)/text_id(必填)
- **响应:** 唯一记录 + 内部 id
- **校验:** 0条返回 404；多条返回 409

## 数据模型
```sql
ALTER TABLE text_main
  ADD COLUMN text_id BIGINT NOT NULL;

ALTER TABLE text_main
  ALTER COLUMN part TYPE INTEGER USING part::INTEGER;

DROP INDEX IF EXISTS uq_text_main_fid_part;
CREATE INDEX idx_text_main_fid ON text_main(fid);
CREATE INDEX idx_text_main_fid_part ON text_main(fid, part);
CREATE INDEX idx_text_main_text_id ON text_main(text_id);
CREATE INDEX idx_text_main_fid_text_id ON text_main(fid, text_id);
CREATE INDEX idx_text_main_part1 ON text_main(fid) WHERE part = 1;
```

## 安全与性能
- **安全:** 所有 by-textid 查询在应用层校验重复并直接报错，避免误操作；导入后提供校验脚本/接口用于巡检重复。
- **性能:** 父/子列表接口分离；子列表强制 fid 过滤；新增索引保证 80 万行规模的分页与排序性能。

## 测试与部署
- **测试:** API 集成测试覆盖父/子列表分页与 textId 查询；详情/编辑按 fid+textId 查询的 404/409 分支。
- **部署:** 迁移时清空旧数据后导入新数据；导入完成后运行重复校验脚本确认无重复。
