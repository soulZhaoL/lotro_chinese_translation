# 技术设计: 旧版导入异常译文修复 SQL 生成

## 技术方案

### 核心技术
- Python 3
- `openpyxl`
- 规则参照 `tools/valid_format/xlsx_to_insert_segmented.py`
- 独立修复脚本 `tools/fix_textid/generate_translation_fix_sql_from_xlsx.py`
- MySQL `UPDATE` 脚本生成

### 实现要点
- 在 `tools/fix_textid/` 下新增一个专用修复脚本，输入为：
  - 新版源文件 `work_text/U46.1.xlsx`
  - 差异样本 `work_text/大括号差异样本_未修正.xlsx`
  - 差异样本 `work_text/竖号差异样本_未修正.xlsx`
- 修复脚本不重新发明规则，直接复用 `xlsx_to_insert_segmented.py` 的以下能力：
  - `fid + splitPart` 合并
  - 三类协议头正则解析
  - 原文/译文分段数量一致性校验
  - `sourceTextHash` 计算
- 脚本先把新版 `U46.1.xlsx` 解析成内存索引：
  - 键：`(fid, textId)`
  - 值：`part, sourceText, sourceTextHash, translatedText`
- 再把两份差异样本合并成待修复索引：
  - 键：`(fid, textId)`
  - 值：`sampleSourceText, sampleBrokenTranslatedText, sample来源`
- 对每个待修复键执行严格匹配：
  - 必须在新版解析结果中找到唯一一条
  - 样本原文若存在，必须与新版解析结果的 `sourceText` 一致
  - 若不一致则直接报错并写入未匹配报告
- 最后生成两类结果：
  - 正式修复 SQL：`tmp_fix_text_main_translated_text.sql`
  - 审计结果：`tmp_fix_text_main_translated_text_report.csv`

## 架构决策 ADR
### ADR-001: 修复范围限定为差异样本命中集合
**上下文:** 现在的问题并不是“新版 Excel 全量更优”，而是“旧版导入污染了数据库中的部分记录”。如果直接根据新版解析结果对整表生成覆盖 SQL，等于把一次修复任务扩成一次全量重灌，风险明显过大。  
**决策:** 仅对差异样本中的 `fid + textId` 生成更新语句。  
**理由:** 最小化影响范围，便于核对、抽样和回滚。  
**替代方案:**  
- 全量 `UPSERT`/整表重刷 → 风险高，且会覆盖后续人工修订  
- 只按正则再次扫描数据库找问题 → 会遗漏样本外上下文，且无法直接给出正确修复值  
**影响:** 需要先合并并去重两份差异样本，形成唯一修复目标集。

### ADR-002: UPDATE 必须携带“当前错误译文”保护条件
**上下文:** 你给的是“曾经有问题的 fid+textId 样本”，不是“当前数据库仍然有问题”的强保证。如果数据库后来有人修过，单靠 `fid + textId` 更新会把正确内容覆盖掉。  
**决策:** 生成 SQL 时，`WHERE` 至少包含 `fid`、`textId`、`translatedText = 样本错误译文`。  
**理由:** 这能把修复限定为“当前仍处于样本错误值”的记录，是最保守也最靠谱的做法。  
**替代方案:**  
- 仅按 `fid + textId` 更新 → 误伤风险不可接受  
- 只按 `sourceTextHash` 更新 → 不能替代业务键，且有理解成本  
**影响:** 若数据库当前值已变，会导致该 SQL 不命中；这类记录必须进入复核清单，而不是被强改。

### ADR-003: 核对逻辑增加原文一致性校验
**上下文:** 样本文件本身已经带了原文列，不用它就是浪费。只拿 `fid + textId` 匹配虽然大概率够用，但少了一层防错。  
**决策:** 当样本 `原文` 非空时，必须与新版解析出的 `sourceText` 完全一致，否则视为异常。  
**理由:** 这是低成本高收益的二次校验，可以及时发现样本错位、解析错误或 Excel 版本不一致。  
**替代方案:**  
- 不做原文校验 → 出错时只能靠人工追查  
**影响:** 会多产出少量“需人工复核”的异常项，但这是好事，不是坏事。

## 数据模型
```sql
-- 目标表结构关键字段
UPDATE text_main
SET
  translatedText = '新版 Excel 解析得到的正确译文',
  sourceText = '新版 Excel 解析得到的原文',
  sourceTextHash = '新版 Excel 计算出的哈希',
  status = status
WHERE fid = '620757435'
  AND textId = '217654768:::118736708-158153749'
  AND translatedText = '你还需要#1:<--DO_NOT_TOUCH!-->可用经验#1:{point[1]';
```

说明：
- `status = status` 不是真实逻辑，只表示本次默认不修改状态字段
- 是否更新 `sourceText/sourceTextHash` 由脚本参数控制；默认建议一并更新，确保数据和新版源文件一致
- `part` 不进入 `WHERE`，因为当前表上 `(fid, textId)` 已有唯一约束；但报告里保留 `part` 供人工核对

## 安全与性能
- **安全:** 样本合并时若同一 `fid + textId` 对应多个不同错误译文，直接报错并终止
- **安全:** 新版解析结果若对同一 `fid + textId` 解析出重复记录，直接报错并终止
- **安全:** 所有未匹配、重复匹配、原文不一致记录必须输出到报告文件，禁止静默忽略
- **性能:** 先在内存建立字典索引，再按样本键查找，复杂度主要取决于 Excel 解析一次 + 样本遍历一次，适合当前离线修复场景

## 测试与部署
- **测试:**
  - 用样本中的典型异常记录验证能生成正确 SQL
  - 验证两份样本重叠项只生成一条更新
  - 验证数据库保护条件 SQL 形态正确
  - 验证未匹配/原文不一致/重复冲突会直接失败或进入报告
- **部署:**
  1. 先在本地生成修复 SQL 与报告
  2. 抽样核对 5-10 条高风险记录
  3. 在数据库执行前先备份目标记录
  4. 执行 SQL 后再跑一次格式巡检，确认大括号和竖号异常已消除
