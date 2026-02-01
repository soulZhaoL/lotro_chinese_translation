# 任务清单: 文本表状态与DML生成

目录: `helloagents/plan/202601312318_text_schema_dml/`

---

## 1. 数据库结构调整
- [√] 1.1 在 `server/migrations/001_init.sql` 中增加建表前 DROP 逻辑、text_main 状态枚举调整、is_claimed 字段、字段注释与约束
- [√] 1.2 补充所有表/字段注释与枚举说明

## 2. 数据导入脚本
- [√] 2.1 解析 `work_text/text_work.xlsx` 前10000行，生成 `work_text/text_main_insert_10000.sql` 插入语句（status=新增，is_claimed=false）

## 3. 文档更新
- [√] 3.1 更新 `helloagents/wiki/data.md` 反映 text_main 状态与认领字段变化
- [√] 3.2 更新 `helloagents/CHANGELOG.md` 与 `helloagents/history/index.md`

## 4. 安全检查
- [√] 4.1 确认 DROP TABLE 为需求明确指示，避免误用

## 5. 测试
- [√] 5.1 手工抽样检查生成 SQL 行数与字段映射
