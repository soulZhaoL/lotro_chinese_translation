# 任务清单: 文本导出下载反馈对齐

目录: `helloagents/history/2026-03/202603291030_export_download_feedback/`

---

## 1. 前端交互修复
- [√] 1.1 为 `downloadFilteredFile` 接入下载进度回调参数
- [√] 1.2 为“导出”按钮增加 loading 状态与阶段文案
- [√] 1.3 将“下载汉化包”文案逻辑改为复用统一格式化函数

## 2. 文档同步
- [√] 2.1 更新 `helloagents/wiki/modules/text.md`，补充下载接口与按钮交互说明
- [√] 2.2 更新 `helloagents/CHANGELOG.md` 与 `helloagents/history/index.md`

## 3. 验证
- [√] 3.1 运行 `npm run build` 验证前端构建通过
- [ -] 3.2 手动点击页面验证真实下载交互（当前会话未启动浏览器）
