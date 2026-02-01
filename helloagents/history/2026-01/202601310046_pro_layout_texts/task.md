# 任务清单: Pro 风格前端 + 文本列表增强 + API/Mock 对齐

目录: `helloagents/plan/202601310046_pro_layout_texts/`

---

## 1. 前端依赖与布局
- [√] 1.1 引入 Ant Design Pro Components 依赖并调整 `web/src/App.tsx` 为 ProLayout 风格
- [√] 1.2 按模块创建页面结构（文本列表/文本详情/翻译编辑/更新记录）

## 2. 文本列表与查询
- [√] 2.1 使用 ProTable 实现查询字段（fid/状态/原文关键字/汉化关键字/更新时间范围/认领人/是否认领）
- [√] 2.2 列表操作列增加认领/释放/编辑/更新记录入口
- [√] 2.3 编号列作为详情入口

## 3. 后端 API 增补
- [√] 3.1 扩展 GET /texts 查询参数支持
- [√] 3.2 新增 DELETE /claims/{id} 释放认领
- [√] 3.3 新增 PUT /texts/{id}/translate 保存译文并写入变更记录
- [√] 3.4 更新 `helloagents/wiki/api.md`

## 4. Mock 对齐
- [√] 4.1 同步更新 `web/mock/*.ts` 覆盖新增字段与接口
- [√] 4.2 确保 Mock 响应字段与后端一致

## 5. 后端测试
- [√] 5.1 增补 tests 覆盖新增接口

## 6. 文档与变更同步
- [√] 6.1 更新 `docs/frontend.md`（Pro 风格与查询字段说明）
- [√] 6.2 更新 `helloagents/CHANGELOG.md`

---

## 任务状态符号
- `[ ]` 待执行
- `[√]` 已完成
- `[X]` 执行失败
- `[-]` 已跳过
- `[?]` 待确认
