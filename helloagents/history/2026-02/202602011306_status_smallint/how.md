# 技术设计: 文本状态改为数值枚举

## 技术方案

### 核心技术
- PostgreSQL SMALLINT + CHECK 约束
- FastAPI 查询参数校验
- React 前端状态映射

### 实现要点
- 数据库: text_main.status 改为 SMALLINT，默认 1，约束为 1/2/3，并在注释中说明映射。
- 后端: /texts status 筛选参数改为 int；保存译文时标记完成则置 3，否则置 2。
- 前端: status 字段改为 number，新增映射表用于展示与筛选。
- 工具: xlsx_to_insert.yaml 将 status 固定为 1；xlsx_to_insert.py 增加 status 固定值为整数的校验。

## 数据模型
```sql
-- status: 1=新增, 2=修改, 3=已完成
status SMALLINT NOT NULL DEFAULT 1
  CONSTRAINT chk_text_main_status CHECK (status IN (1, 2, 3))
```

## 安全与性能
- **安全:** 仅变更字段类型与校验，不涉及权限逻辑。
- **性能:** 数值枚举降低索引与比较成本。

## 测试与部署
- **测试:** 手动验证 /texts?status=1/2/3 与保存译文状态变更。
- **部署:** 重新执行迁移脚本（如已有数据需先迁移）。
