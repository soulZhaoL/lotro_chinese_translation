# 技术设计: 文本导出下载反馈对齐

## 技术方案

### 前端（`web/src/modules/texts/list/filter.tsx`）
- 为 `downloadFilteredFile` 增加可选 `onProgress` 参数，复用既有 `downloadByPath()` 的进度分发能力。
- 新增 `formatDownloadProgressText()`，统一处理“生成中 / 传输中百分比 / 传输中已接收大小”三类文案。
- 扩展 `SearchActionBar` 属性，使“导出”按钮支持独立的 loading 状态与动态文案。

### 前端（`web/src/modules/texts/list/index.tsx`）
- 新增“导出”按钮本地状态：下载中标记与阶段文案。
- 在 `handleDownloadFiltered()` 中接入进度回调，点击后先显示“导出生成中...”，后续根据回调更新文案。
- “下载汉化包”切换为复用同一文案格式化函数，避免两处逻辑不一致。

## 安全与性能
- **安全:** 无新增权限面，仍走现有认证下载链路。
- **性能:** 仅增加前端状态更新，不改变实际下载实现与服务端负载。

## 测试与验证
- 运行 `npm run build`，验证 TypeScript 类型与 Vite 构建通过。
- 手动验证“导出”按钮点击后出现 loading 和阶段文案，完成后恢复默认文本。
