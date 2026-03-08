# 技术设计：下载汉化包功能

## 技术方案

### 后端（server/routes/texts.py）

#### 新增常量
```python
PACKAGE_HEADERS = ("fid", "part_range", "sourceText", "translatedText")
```

#### 新增辅助函数

**`_format_part_range(parts: List[int]) -> str`**
- 将 part 列表压缩为范围字符串
- [1,2,3] → "1-3"，[1] → "1-1"，[1,2,4,5] → "1-2,4-5"

**`_merge_fid_rows(fid_rows: List[Dict]) -> Tuple[str, str, str, str]`**
- 合并同一 fid 的多个 part 为一行 Excel 数据
- 格式化为 `textId:::::::[text]`（6冒号协议格式）
- 用 `|||` 连接各段
- 空 translatedText 取 sourceText 填充

#### 新增路由
`GET /texts/download-package`
- 参数：复用现有所有筛选参数（fid/status/sourceKeyword 等）
- 查询：`ORDER BY fid ASC, part ASC`（保证按 fid 连续排列）
- 流式处理：按 fid 顺序逐行读取，同一 fid 缓存到 buffer，fid 变化时 flush
- 内存控制：buffer 只保存当前 fid 的行，不全量加载
- 写入：write_only 模式 Workbook，分批处理
- 输出：FileResponse + BackgroundTask 清理临时文件

### 性能策略

| 问题 | 方案 |
|------|------|
| 80万行全量加载 OOM | 流式查询 db_stream_cursor() + 逐 fid flush |
| Excel 写入内存占用 | write_only Workbook 模式 |
| 临时文件清理 | BackgroundTask（与现有导出一致） |
| fid buffer 大小 | 最多持有 1 个 fid 的行（通常 ≤几十行） |

### 前端（web/src/modules/texts/list/filter.tsx）

#### 新增函数
```typescript
export async function downloadPackageFile(search: QueryParams): Promise<DownloadFileResult>
```
- 复用现有 `buildDownloadQuery` 和 `downloadByPath`
- 调用路径：`/texts/download-package?{params}`
- Mock 模式提示："Mock 模式不支持汉化包下载"

#### SearchActionBarProps 扩展
```typescript
type SearchActionBarProps = {
  // ...现有字段...
  onDownloadPackage: () => void;
};
```

#### 按钮位置
`[导出] [下载汉化包] [下载模板] [上传译文]`

### 前端（web/src/modules/texts/list/index.tsx）

#### 新增 handler
```typescript
const handleDownloadPackage = useCallback(async () => {
  const currentSearch = resolveSearchParams(formRef, parentSearch);
  // 不需要 hasAnyFilter 检查（汉化包无筛选条件时导出全部）
  try {
    const result = await downloadPackageFile(currentSearch);
    if (result === "mock_unsupported") {
      message.warning("Mock 模式不支持汉化包下载");
      return;
    }
    message.success("汉化包下载成功");
  } catch (error) {
    message.error(getErrorMessage(error, "汉化包下载失败"));
  }
}, [parentSearch]);
```

## 安全与性能

- 需登录认证（require_auth）
- 沿用 max_download_rows 配置限制行数（按 fid 分组后的行数）
- 临时文件自动清理
