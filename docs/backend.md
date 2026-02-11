# 后端使用说明

## 环境依赖

- Python 3.11+
- PostgreSQL 14+

## 安装依赖

在项目根目录执行：

```
pip install -r requirements.txt
```

## 配置说明

配置文件固定为 `config/lotro.yaml`，其中敏感信息通过环境变量注入：

- `LOTRO_DATABASE_DSN`
- `LOTRO_TOKEN_SECRET`

在项目根目录创建 `.env`（可参考 `.env.example`），示例：

```
LOTRO_DATABASE_DSN=postgresql://user:password@localhost:5432/lotro
LOTRO_TOKEN_SECRET=replace_with_strong_secret
```

如 `.env` 不在项目根目录，可设置：

```
LOTRO_ENV_PATH=/abs/path/to/.env
```

## 初始化数据库

数据库未初始化时，执行迁移脚本：

```
psql "$LOTRO_DATABASE_DSN" -f server/migrations/001_init.sql
```

若数据库已存在旧版 snake_case 列，请再执行一次驼峰迁移：

```
psql "$LOTRO_DATABASE_DSN" -f server/migrations/002_camel_case_columns.sql
```

## 启动服务

### 一键启动（推荐）

项目根目录提供临时脚本 `tmp_start_dev.sh`，用于一键启动 SSH 隧道与后端（不提供默认值，必须显式配置）：

```
./tmp_start_dev.sh
```

脚本要求显式环境变量配置（避免硬编码敏感信息）：

```
LOTRO_SSH_HOST=43.133.38.166
LOTRO_SSH_USER=ubuntu
LOTRO_SSH_PORT=22
LOTRO_TUNNEL_PORT=5433
LOTRO_REMOTE_DB_HOST=127.0.0.1
LOTRO_REMOTE_DB_PORT=5432
LOTRO_BACKEND_HOST=0.0.0.0
LOTRO_BACKEND_PORT=8000
```

可选：通过 `LOTRO_ENV_PATH` 指定环境文件（脚本会 source 该文件）：

```
LOTRO_ENV_PATH=/abs/path/to/.env
```

说明：脚本不会保存或注入 SSH 密码，使用密码登录时请按终端提示输入。

### 手动启动

```
ssh -N -L 5433:127.0.0.1:5432 ubuntu@43.133.38.166 -p 22
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

### 后台守护（支持启动/停止/状态/重启）

使用 `server/service.sh` 管理服务（必须显式传入环境文件）：

```
./server/service.sh start --env /abs/path/.env
./server/service.sh status --env /abs/path/.env
./server/service.sh stop --env /abs/path/.env
./server/service.sh restart --env /abs/path/.env
```

环境文件需包含以下变量：

```
LOTRO_BACKEND_HOST=0.0.0.0
LOTRO_BACKEND_PORT=8000
LOTRO_PID_PATH=/abs/path/to/uvicorn.pid
LOTRO_LOG_PATH=/abs/path/to/uvicorn.log
```

## API 文档

FastAPI 自带文档：

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

项目内补充文档：`helloagents/wiki/api.md`

核心接口补充：

- 查询：GET /texts（支持高级查询参数）
- 详情：GET /texts/{textId}
- 认领：POST /claims
- 释放认领：DELETE /claims/{claimId}
- 保存译文：PUT /texts/{textId}/translate
- 更新记录：GET /changes?textId=...

## 运行测试

```
pytest -q
```

如需仅运行单个用例：

```
pytest tests/tmp_test_locks.py -q
```

## 常见问题

- 报错“缺少环境变量”: 确认 `.env` 已生效且包含 `LOTRO_DATABASE_DSN`/`LOTRO_TOKEN_SECRET`
- 报错“缺少数据表”: 请先执行迁移脚本

## 性能与传输
- 已启用 GZip 压缩（最小响应大小由 `config/lotro.yaml` 的 `http.gzip_minimum_size` 控制）
