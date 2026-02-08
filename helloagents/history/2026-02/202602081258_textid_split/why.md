# 变更提案: textId拆分与嵌套列表

## 需求背景
当前从游戏 dat 提取的文本以 fid 为单位聚合多个 textId，导致版本更新时难以精准定位单段文本变动。为提升比对与编辑精度，需要按 textId 拆分存储，并在列表端提供分组/嵌套展示与子列表分页查询，同时编辑/详情按 fid+textId 精确定位。

## 变更内容
1. 数据模型：`text_main` 新增 `text_id`，`part` 仅作为顺序自增，不设唯一约束；补充必要索引以支持父/子列表高效查询。
2. 接口拆分：新增父列表与子列表专用接口；新增 fid+textId 详情查询接口；对重复 textId 做应用层校验并直接报错。
3. 前端交互：主列表改为嵌套子列表（外层 fid+part=1，子列表按 part 升序）；子列表支持 textId 查询与分页；详情/编辑按 fid+textId 进入，返回需恢复进入前的列表状态。

## 影响范围
- **模块:** 文本任务与翻译（列表、详情、编辑）、数据模型、API
- **文件:** server/migrations/001_init.sql, server/routes/texts.py, web/src/modules/texts/pages/TextsList.tsx, web/src/modules/texts/pages/TextDetail.tsx, web/src/modules/texts/pages/TextEdit.tsx, web/src/App.tsx, web/mock/*
- **API:** /texts/parents, /texts/children, /texts/by-textid（新增）
- **数据:** text_main 新增 text_id；移除 fid+part 唯一约束；新增索引

## 核心场景
### 需求: 父列表嵌套展示
**模块:** 文本任务与翻译
外层列表只展示 part=1 的记录，点击展开查看同 fid 的所有拆分记录。

#### 场景: 浏览父列表
用户进入文本列表
- 外层列表展示 fid + part=1
- 支持分页与现有筛选条件

### 需求: 子列表查询与分页
**模块:** 文本任务与翻译
子列表展示同 fid 的所有拆分记录，并支持 textId 查询与分页。

#### 场景: 展开 fid 子列表
用户展开某 fid 行
- 子列表按 part 升序
- 支持 textId 查询与分页

### 需求: 详情/编辑按 fid+textId 定位
**模块:** 文本任务与翻译
详情与编辑按 fid+textId 精确查询，保存仍更新该 textId 对应记录。

#### 场景: 从子列表进入编辑
用户点击某条 textId
- 详情/编辑页按 fid+textId 查询
- 保存后返回列表，保持进入前的查询与展开状态

## 风险评估
- **风险:** 未设唯一约束导致重复 textId 数据混入
  - **缓解:** 应用层查询时检测重复并返回 409；提供校验脚本/接口用于导入后巡检
- **风险:** 子列表分页与筛选混用主列表接口导致性能退化
  - **缓解:** 拆分父/子列表专用接口，强制按 fid 过滤并加索引
- **风险:** 返回状态丢失影响编辑效率
  - **缓解:** 前端持久化父列表查询条件、展开行及子列表分页/筛选状态
