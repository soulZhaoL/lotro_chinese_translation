# 任务清单: xlsx 固定格式计数脚本

目录: `helloagents/plan/202602021030_xlsx_format_check/`

---

## 1. 工具脚本
- [√] 1.1 在 `tools/xlsx_format_check.py` 中实现固定格式分段与计数函数，验证 why.md#需求-固定格式计数-场景-预览前100行计数
- [√] 1.2 在 `tools/xlsx_format_check.py` 中实现 xlsx 读取与 CLI 输出（含可选 C/D 对比），验证 why.md#需求-固定格式计数-场景-原文译文数量对比

## 2. 文档更新
- [√] 2.1 更新 `helloagents/wiki/modules/validation.md` 补充离线固定格式计数脚本说明

## 3. 安全检查
- [√] 3.1 执行安全检查（按G9: 输入验证、敏感信息处理、权限控制、EHRB风险规避）

## 4. 测试
- [√] 4.1 手动运行脚本解析 `work_text/text_work.xlsx` 前100行，核对输出计数
