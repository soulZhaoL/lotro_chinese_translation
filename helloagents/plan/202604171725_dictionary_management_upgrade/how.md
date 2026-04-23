# 技术设计: 词典管理菜单升级

## 技术方案

### 核心技术
- 前端: React + Ant Design + Ant Design Pro `ProTable`
- 后端: FastAPI
- 文件处理: `openpyxl`
- 数据库: MySQL

### 实现要点
- 词典页面从手写 `Form + Table` 切换为与文本管理一致的 `ProTable` 结构。
- 搜索区复用文本管理的布局思路：左侧搜索动作，右侧业务动作按钮。
- 新增单条修改弹窗，原文 key 只读，允许维护 `termValue/category/remark`。
- 新增词典模板下载、筛选结果导出、模板导入接口，模板和导出列顺序严格一致。
- 列表与接口增加 `remark/lastModifiedBy/lastModifiedByName` 字段，前端展示修改人与备注。

## 架构决策 ADR

### ADR-20260417-01: 词典导入导出沿用文本管理的 xlsx 模板机制
**上下文:** 项目文本管理已经具备成熟的模板下载、文件下载、二进制上传交互与后端解析逻辑。词典模块新增导入导出时，可以复用同类交互模型。
**决策:** 词典导入导出统一使用 xlsx，下载模板与导出文件字段完全一致，上传走二进制 body。
**理由:** 可保持用户心智一致，复用现有文件交互模式，降低前后端实现分歧。
**替代方案:** CSV 导入导出 → 拒绝原因: 与文本管理不一致，中文字段和编码兼容成本更高。
**影响:** 后端需新增词典模板校验逻辑，前端需补齐下载进度/上传反馈按钮。

### ADR-20260417-02: 用原文 key 作为导入幂等键，并在数据库层保证唯一
**上下文:** 用户明确要求导入时“原文 key 存在则覆盖，不存在则新增”，这要求系统能够稳定按 key 识别唯一词条。
**决策:** 为 `dictionary_entries.termKey` 增加唯一约束；导入阶段按 `termKey` 执行 upsert 语义。
**理由:** 只有数据库约束才能从根上保证覆盖行为可预测，避免脏数据导致多条同 key。
**替代方案:** 仅在应用层查重 → 拒绝原因: 无法防止并发写入和历史脏数据持续产生。
**影响:** 需要在迁移前补一次重复 key 清理检查。

## API设计

### [GET] /dictionary
- **请求:** `termKey`、`termValue`、`category`、`page`、`pageSize`
- **响应:** `items/total/page/pageSize`
- **增强字段:** 每条记录新增 `remark`、`lastModifiedBy`、`lastModifiedByName`

### [POST] /dictionary
- **请求:** `termKey`、`termValue`、`category?`、`remark?`
- **响应:** `id`
- **规则:** 新增时默认 `isActive=true`，`lastModifiedBy` 写当前用户

### [PUT] /dictionary/{entryId}
- **请求:** `termValue`、`category?`、`remark?`
- **响应:** `id`
- **规则:** 不允许修改 `termKey`；保存后更新 `lastModifiedBy`、`uptTime`

### [GET] /dictionary/template
- **请求:** 无
- **响应:** xlsx 模板文件
- **表头:** `原文 key`、`译文 value`、`分类`、`备注`

### [GET] /dictionary/download
- **请求:** 复用列表筛选参数
- **响应:** xlsx 数据文件
- **规则:** 导出列顺序与模板完全一致

### [POST] /dictionary/upload
- **请求:** `fileName`（query） + xlsx 二进制 body
- **响应:** `createdCount`、`updatedCount`
- **规则:**
  - 表头必须严格匹配模板
  - `原文 key`、`译文 value` 必填
  - 同一导入文件中若出现重复 `原文 key`，直接报错并终止导入
  - 全量校验通过后，再统一写库；任一异常整批回滚

## 数据模型

```sql
ALTER TABLE dictionary_entries
  ADD COLUMN remark VARCHAR(255) NULL COMMENT '备注' AFTER category,
  ADD COLUMN `lastModifiedBy` BIGINT NULL COMMENT '最后修改人ID' AFTER `isActive`;

CREATE UNIQUE INDEX uq_dictionary_term_key ON dictionary_entries(`termKey`);
CREATE INDEX idx_dictionary_category ON dictionary_entries(category);
CREATE INDEX idx_dictionary_last_modified_by ON dictionary_entries(`lastModifiedBy`);
```

### 查询模型补充
- 列表查询时 `LEFT JOIN users u ON u.id = de.lastModifiedBy`
- 响应补充 `lastModifiedByName = u.username`

### 导入覆盖规则
- 命中已有 `termKey`:
  - 覆盖 `termValue`
  - 覆盖 `category`
  - 覆盖 `remark`
  - 保留原 `isActive`
  - 更新 `lastModifiedBy`、`uptTime`
- 未命中 `termKey`:
  - 新增记录
  - `isActive = true`
  - 写入 `lastModifiedBy`、`crtTime`、`uptTime`

## 前端交互设计

### 页面结构
- 将 `web/src/modules/dictionary/index.tsx` 重构为 `ProTable` 页面，与文本管理一致：
  - `headerTitle`
  - `search.optionRender`
  - `request` 驱动分页查询
  - `toolBarRender={false}`

### 搜索区
- 查询字段保留:
  - 原文 key
  - 译文 value
  - 分类
- 操作栏对齐文本管理:
  - 左侧: 查询、重置
  - 右侧: 导出、下载模板、导入、新增

### 列表列
- 原文 key
- 译文 value
- 分类
- 备注
- 修改人
- 更新时间
- 操作

### 展示规则
- `备注` 使用与文本管理一致的长文本截断 + `Popover` 展示
- `修改人` 优先显示用户名，缺失时显示 `-`
- `分类` 继续复用 `CATEGORY_LABELS`

### 新增/修改弹窗
- 建议使用同一个表单弹窗，区分“新增”和“修改”模式
- 新增模式:
  - `termKey` 可编辑
  - `termValue` 必填
  - `category` 可选
  - `remark` 可选
- 修改模式:
  - `termKey` 只读
  - 允许编辑 `termValue/category/remark`

### 导入导出交互
- 下载模板: 直接下载 xlsx 模板
- 导出: 读取当前筛选参数，按钮展示“导出生成中/传输中”状态
- 导入:
  - 点击按钮触发隐藏文件选择器
  - 限制 `.xlsx`
  - 成功提示“新增 X 条，覆盖 Y 条”
  - 失败展示后端返回的首个明确错误

## 安全与性能
- **安全:**
  - 词典写接口继续走鉴权
  - 导入执行严格表头校验、必填校验、重复 key 校验
  - 单次导入使用事务，避免半成功状态
- **性能:**
  - 列表改为服务端分页，避免一次性固定加载 50 条
  - 导出沿用流式文件返回思路，避免大批量数据堆内存

## 测试与部署
- **测试:**
  - 词典列表查询与分页
  - 新增词条含备注
  - 修改词条仅允许更新 `termValue/category/remark`
  - 模板下载表头校验
  - 导出列顺序校验
  - 导入新增场景
  - 导入覆盖场景
  - 导入重复 key/空 key/错误表头失败场景
  - 前端按钮状态与列表刷新验证
- **部署:**
  - 先执行数据库迁移与历史重复 key 检查
  - 后端接口上线后再发布前端
  - mock 数据同步补齐新字段与新接口
