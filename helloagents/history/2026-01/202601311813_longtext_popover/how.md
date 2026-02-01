# 技术设计: 长文本预览交互优化（Popover 限高滚动）

## 技术方案

### 核心技术
- Ant Design Popover
- CSS 限高 + overflow

### 实现要点
- 将 Tooltip 替换为 Popover，内容容器设置 `maxHeight` 与 `overflowY: auto`
- 维持列表内的截断显示逻辑，Popover 内展示更完整文本
- 限制 Popover 宽度，避免遮挡其它列

## 安全与性能
- **安全:** 无新增数据暴露
- **性能:** 仅前端展示优化，不影响接口

## 测试与部署
- **测试:** 手动验证长文本 hover 不遮挡整屏，滚动可读
- **部署:** 前端静态资源
