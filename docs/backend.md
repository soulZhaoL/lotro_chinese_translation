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

## 启动服务
```
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

## API 文档
FastAPI 自带文档：
- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

项目内补充文档：`helloagents/wiki/api.md`

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
