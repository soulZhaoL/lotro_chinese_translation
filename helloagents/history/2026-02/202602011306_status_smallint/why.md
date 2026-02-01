# 变更提案: 文本状态改为数值枚举

## 需求背景
当前 text_main.status 使用字符串（新增/修改/已完成），与“枚举应使用 tinyint(3) 自增”的要求冲突，且在筛选与索引上存在额外存储成本。需要全局统一为数值枚举，并同步 API/前端/脚本与文档。

## 变更内容
1. 将 text_main.status 改为 SMALLINT（1=新增，2=修改，3=已完成），保持 is_claimed 为 boolean。
2. 全局更新后端接口、前端展示与 mock 数据的状态类型与映射。
3. 更新批量导入脚本与配置，使 status 输出为数值枚举。

## 影响范围
- **模块:** 后端文本模块、前端文本模块、导入工具、文档
- **文件:** server/migrations/001_init.sql, server/routes/texts.py, web/src/modules/texts/*, web/mock/*, tools/xlsx_to_insert.py, tools/xlsx_to_insert.yaml, helloagents/wiki/*, helloagents/CHANGELOG.md
- **API:** /texts 列表、/texts/{id} 详情、/texts/{id}/translate
- **数据:** text_main.status 字段类型及含义

## 核心场景

### 需求: 状态枚举数值化
**模块:** 文本任务与翻译
将状态字段持久化为数值枚举，并通过映射输出到 UI。

#### 场景: 查询筛选与展示
客户端按 status=1/2/3 筛选；UI 以“新增/修改/已完成”展示。
- 预期结果: 筛选与展示一致

#### 场景: 保存译文
保存时若标记完成则 status=3，否则 status=2。
- 预期结果: 状态符合业务含义

## 风险评估
- **风险:** PostgreSQL 无 tinyint 类型，需使用 SMALLINT 替代；现有数据若已入库需额外迁移。
- **缓解:** 明确采用 SMALLINT 并在注释中标注映射；如已有数据需执行数据迁移脚本（另行补充）。
