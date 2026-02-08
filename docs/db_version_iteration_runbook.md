# 文本库版本迭代运行手册（换表方案）

## 1. 目标

本手册用于在不引入“主表无限膨胀”的前提下完成版本升级（如 U46 → U46.1）：

1. 旧主表备份为归档表。
2. 新版本构建在独立表中完成比对与译文继承。
3. 切换时将新表替换为 `text_main`。
4. 关联表按明确策略处理，避免数据错乱。

---

## 2. 本方案已确认的业务策略

你已确认以下规则，本手册按此执行：

1. `text_main` 先备份为 `text_main_bak_<version_tag>`。
2. 新版本在 `text_main_next` 中构建。
3. 匹配规则命中后复制译文，并分类状态：
   - 新增
   - 修改
   - 未变化（继承旧状态，**不强制改为已完成**）
4. `text_claims`、`text_locks` 全量清空。
5. `text_changes` 按映射迁移：
   - 有新老 ID 映射关系：替换为新 ID
   - 无映射关系：删除
6. 切换期间执行全员下线，禁止用户继续编辑。

---

## 3. 关键风险与防护

## 3.1 线上编辑冲突风险（必须处理）

如果用户正在编辑旧 `text_main.id`，同时发生换表，会出现：

- 提交写入旧 ID（切换后不存在）
- 误写到错误文本
- 前端页面显示和数据库不一致

**强制防护动作：**

1. 进入维护窗口（读写冻结）。
2. 全员踢下线（使现有 token 立即失效）。
3. 清空锁和认领。
4. 完成换表后再开放登录。

## 3.2 全员下线实现建议（基于当前项目）

当前 token 为 HMAC 自签且服务端无会话表（`server/services/auth.py`），要“立即失效全部 token”，最直接方案是：

1. 更换 `auth.token_secret`（配置文件或环境变量）
2. 重启后端服务

效果：历史 token 签名全部失效，用户需重新登录。

---

## 4. 命名规范（一次迭代）

以 `U46 -> U46.1` 为例：

- 在线主表（升级前）：`text_main`
- 备份表：`text_main_bak_u46`
- 新版本工作表：`text_main_next`
- ID 映射表：`text_id_map_u46_to_u46_1`

说明：表名统一小写，版本号中的 `.` 替换为 `_`。

---

## 5. 迁移前置条件

必须全部满足：

1. 新版本 dat 已解包为 `fid + text_id + part + source_text`。
2. 已计算 `source_text_hash`（SHA256）。
3. 维护窗口已申请并通知全员。
4. 已完成数据库全量备份（物理或逻辑备份）。

---

## 6. 标准执行步骤（SOP）

## Step 0：进入维护窗口 + 全员下线

1. 后端切维护模式（拒绝写接口，推荐临时拒绝登录）。
2. 更换 `token_secret` 并重启后端，强制旧 token 失效。
3. 通知前端“请重新登录，系统升级中”。

## Step 1：冻结会话态关联数据

执行：

1. 清空 `text_locks`。
2. 清空 `text_claims`。

说明：这两张表是会话态数据，不做跨版本迁移。

## Step 2：备份当前主表

1. 校验不存在同名备份表。
2. 执行重命名：`text_main` → `text_main_bak_u46`。
3. 校验备份表行数（预期约 80 万）。

## Step 3：创建新主表骨架

1. 以 `text_main_bak_u46` 的结构创建 `text_main_next`（含索引）。
2. 建议新增列（如尚未存在）：`source_text_hash`。
3. 对 `text_main_next` 建唯一约束：`(fid, text_id, part)`。

## Step 4：导入新版本原文到 `text_main_next`

导入字段建议：

- `fid`
- `text_id`
- `part`
- `source_text`
- `source_text_hash`
- `translated_text`（初始 NULL）
- `status`（初始按规则计算）
- `is_claimed`（固定 FALSE）
- `edit_count`（初始 0）
- `updated_at` / `created_at`

## Step 5：与备份表比对并继承译文

比对键：`fid + text_id + part`

判定规则：

1. 备份不存在该键 → `status=1(新增)`。
2. 备份存在且 `source_text_hash` 不同 → `status=2(修改)`，不继承译文。
3. 备份存在且 `source_text_hash` 相同 → 继承旧 `translated_text/status/edit_count`。

**严格禁止**：使用“文本长度相同”作为匹配条件。

## Step 6：生成新老 ID 映射表（供 `text_changes` 迁移）

建立映射表 `text_id_map_u46_to_u46_1`：

- `old_id`
- `new_id`

映射条件：

1. `fid + text_id + part` 命中
2. 且 `source_text_hash` 相同（仅对稳定文本建立映射）

## Step 7：迁移 `text_changes`

你确认的策略如下执行：

1. 仅保留 `text_changes.text_id` 在映射表中可命中的记录。
2. 将命中记录的 `text_id` 批量替换为 `new_id`。
3. 未命中记录直接删除。

说明：该策略会丢弃“变更后已失配文本”的历史，这是你当前明确接受的取舍。

## Step 8：原子切换主表

在单事务中执行：

1. 校验 `text_main_next` 数据完整。
2. 重命名 `text_main_next` → `text_main`。
3. 保留 `text_main_bak_u46` 不删除（观察期内可回滚）。

注意：不在切换事务中执行大规模 DML，避免持锁过长。
注意：切换瞬间接口可能出现短暂失败（锁等待/对象重命名窗口），必须在维护窗口内执行，且前端处于阻断访问状态。

## Step 9：发布后校验

至少检查：

1. `text_main` 行数与新版本导入预期一致。
2. 新增/修改/继承三类统计与 Step 5 报表一致。
3. `text_claims`、`text_locks` 为空。
4. `text_changes` 不存在悬空 `text_id`。
5. 核心接口可用：`/texts/parents`、`/texts/children`、`/texts/{id}`、`/texts/{id}/translate`。

## Step 10：解除维护窗口

1. 恢复登录与写接口。
2. 通知全员重新登录。
3. 观察运行状态（建议至少 24 小时）。

---

## 7. 回滚方案

若发布后异常：

1. 重新进入维护窗口并全员下线。
2. 在事务内：
   - 当前 `text_main` 重命名为 `text_main_bad_<timestamp>`
   - `text_main_bak_u46` 重命名回 `text_main`
3. 恢复服务并复核核心接口。

说明：`text_claims`/`text_locks` 已清空，回滚后仍保持空状态，由业务重新认领。

---

## 8. 执行检查清单（可直接勾选）

- [ ] 已进入维护窗口
- [ ] 已强制全员下线（更新 `token_secret` 并重启）
- [ ] 已清空 `text_claims`
- [ ] 已清空 `text_locks`
- [ ] `text_main` 已备份为 `text_main_bak_<source_version>`
- [ ] `text_main_next` 已完成导入
- [ ] 已完成比对与状态分类
- [ ] 已完成 `text_id_map` 生成
- [ ] `text_changes` 已按映射迁移并清理未命中记录
- [ ] 已完成 `text_main_next -> text_main` 原子切换
- [ ] 发布后校验通过
- [ ] 已解除维护窗口并通知重登

---

## 9. 后续建议（下一阶段优化）

1. 给 `text_changes` 增加版本标签字段，避免历史语义依赖单纯 ID。
2. 给迁移过程增加自动校验脚本（行数、孤儿记录、状态分布）。
3. 将换表流程封装为单独运维脚本，减少人工 SQL 操作误差。

以上优化不影响本次 SOP 执行，但建议在下一次版本迭代前完成。
