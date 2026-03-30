# 汉化包格式差异分析工具

用途：
- 比较 online 导出的 `sheet1(fid/split_part/translation)` 与 sys 导出的 `texts(fid/translation)`
- 验证两边是否只是“文本内容”不同，还是已经存在协议/分片格式差异

特点：
- 不依赖 `openpyxl`、`PyYAML`
- 直接解析 xlsx 内部 XML
- 必须通过 JSON 配置文件传参，不使用代码内默认配置

运行方式：

```bash
python3 tools/package_format_diff/analyze_package_xlsx_format.py \
  --config tools/package_format_diff/compare_u46_1_online_vs_sys.json
```

输出：
- 摘要：`tmp/tmp_package_format_diff_summary.md`
- 明细：`tmp/tmp_package_format_diff_report.csv`
