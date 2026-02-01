# 技术设计: 词典筛选解耦与文本列表/编辑体验优化

## 技术方案

### 核心技术
- 前端: React + Ant Design + ProTable
- 后端: FastAPI

### 实现要点
- /dictionary 新增 term_key / term_value 查询参数，兼容现有 keyword。
- 词典筛选拆分为“原文/译文/分类”，新增按钮打开 Modal 表单。
- 文本编辑保存成功后 navigate 回列表，并触发列表刷新。
- 文本列表设置列宽与操作列最小宽度，优化自适应显示。

## API设计
### [GET] /dictionary
- **请求:** keyword(兼容)、term_key、term_value、category、is_active、page、page_size
- **响应:** 维持原结构

## 安全与性能
- **安全:** 不引入新敏感数据
- **性能:** 列宽调整不影响接口性能

## 测试与部署
- **测试:** 手动验证筛选/新增/编辑回跳/列宽
- **部署:** 前端静态资源、后端 API 兼容更新
