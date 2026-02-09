# Changelog

本文件记录项目所有重要变更。
格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/),
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 新增
- 初始数据库迁移脚本（用户/文本/认领/锁定/变更/词典）
- FastAPI 后端骨架与核心接口（认证/文本/锁定/词典/校验）
- YAML 配置文件与依赖清单
- 前端工程骨架（React + Ant Design + Vite）
- 后端集成测试骨架（pytest）
- .env 配置加载与敏感信息占位支持
- docs 使用说明与 MVP 联通指引
- 前端 Mock（vite-plugin-mock）
- 后端单元测试补充（锁定/搜索/词典/校验）
- Pro 风格布局与文本列表增强
- 文本列表新增详情/编辑/更新记录页面与操作入口
- 后端新增译文保存与认领释放接口
- 前端模块化目录结构与 Pro 风格细节优化
- 一键启动脚本（SSH 隧道 + 后端服务）
- 前端操作反馈提示（登录/认领/释放/保存/新增）
- 菜单图标与退出按钮位置优化
- 词典分类枚举映射与筛选下拉
- 主文本列表新增原文/译文/编辑次数展示与长文本悬浮
- 词典筛选拆分为原文/译文字段
- 词典新增弹窗表单
- 文本编辑保存后返回列表并刷新
- xlsx 固定格式计数脚本（支持 C/D 列对比）
- 文本父/子列表专用接口（/texts/parents, /texts/children, /texts/by-textid）
- 主文本列表嵌套子列表（textId 查询 + 分页）
- 详情/编辑页支持 fid + textId 精确查询
- 维护模式配置与全局拦截中间件
- 前端维护页面与维护状态探测

### 变更
- 文本表状态改为数值枚举（1=新增/2=修改/3=已完成），新增认领状态字段 is_claimed
- 迁移脚本补充字段/表注释并在建表前删除已有表
- 生成前10000条文本插入SQL（text_main）
- 新增 xlsx 批量 INSERT 生成脚本（支持行范围与分块）
- text_main.edit_count 默认值调整为 0
- 移除迁移脚本中的外键约束（避免操作阻碍）
- 配置文件路径固定为 `config/lotro.yaml`，不再依赖 LOTRO_CONFIG_PATH
- xlsx 导入脚本将空字符串视为 NULL（可选字段），缺失必填列时输出行号
- xlsx 导入脚本支持跳过空行（避免无效空白触发缺失错误）
- 允许 source_text 为空，并同步导入配置与前端展示兜底
- xlsx 导入脚本支持命令行 row-range 覆盖配置范围
- 前端布局调整为顶部导航 + 左侧二级
- 前端 Mock 依赖升级至 vite-plugin-mock 3.x
- 前端构建工具升级至 Vite 7（修复 esbuild 风险）
- 主文本列表列宽调整（原文/译文扩大，操作列缩小）
- 长文本预览由 Tooltip 改为 Popover（限高滚动）
- text_main 新增 text_id，part 调整为顺序编号并新增索引，移除 fid+part 唯一约束
- xlsx 导入配置新增 text_id 列映射

### 修复
- 数据模型文档补齐 text_locks.released_at 字段

## [0.1.0] - 2026-01-30

### 新增
- 初始化知识库文档结构
