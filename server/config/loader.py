# 配置文件加载与校验。
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv


_REQUIRED_TOP_LEVEL_KEYS = ("database", "auth", "pagination", "locks", "cors", "http", "text_list", "maintenance")
_ENV_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)\}")


class ConfigError(Exception):
    pass


def _require_key(obj: Dict[str, Any], key: str, path: str) -> Any:
    if key not in obj:
        raise ConfigError(f"缺少配置项: {path}{key}")
    return obj[key]


def _require_type(value: Any, expected_type: type, path: str) -> Any:
    if not isinstance(value, expected_type):
        raise ConfigError(f"配置项类型错误: {path} 期望 {expected_type.__name__}")
    return value


def _parse_bool(value: Any, path: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y"}:
            return True
        if normalized in {"false", "0", "no", "n"}:
            return False
    raise ConfigError(f"配置项类型错误: {path} 期望 bool")


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_env_file() -> None:
    env_path = os.environ.get("LOTRO_ENV_PATH")
    if env_path is None:
        default_path = _project_root() / ".env"
        if default_path.exists():
            load_dotenv(default_path, override=False)
        return
    path = Path(env_path)
    if not path.exists():
        raise FileNotFoundError(f"环境文件不存在: {path}")
    load_dotenv(path, override=False)


def _resolve_env_string(value: str) -> str:
    def replacer(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in os.environ:
            raise ConfigError(f"缺少环境变量: {key}")
        return os.environ[key]

    return _ENV_PATTERN.sub(replacer, value)


def _resolve_env(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {key: _resolve_env(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [_resolve_env(item) for item in obj]
    if isinstance(obj, str):
        return _resolve_env_string(obj)
    return obj


def load_config() -> Dict[str, Any]:
    _load_env_file()
    path = _project_root() / "config" / "lotro.yaml"
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {path}")

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    if not isinstance(data, dict):
        raise ConfigError("配置文件根对象必须为 YAML 对象")

    data = _resolve_env(data)

    for key in _REQUIRED_TOP_LEVEL_KEYS:
        if key not in data:
            raise ConfigError(f"缺少配置分组: {key}")

    database = _require_type(_require_key(data, "database", ""), dict, "database")
    auth = _require_type(_require_key(data, "auth", ""), dict, "auth")
    pagination = _require_type(_require_key(data, "pagination", ""), dict, "pagination")
    locks = _require_type(_require_key(data, "locks", ""), dict, "locks")
    cors = _require_type(_require_key(data, "cors", ""), dict, "cors")
    http = _require_type(_require_key(data, "http", ""), dict, "http")
    text_list = _require_type(_require_key(data, "text_list", ""), dict, "text_list")
    maintenance = _require_type(_require_key(data, "maintenance", ""), dict, "maintenance")

    _require_type(_require_key(database, "dsn", "database."), str, "database.dsn")

    _require_type(_require_key(auth, "hash_algorithm", "auth."), str, "auth.hash_algorithm")
    _require_type(_require_key(auth, "salt_bytes", "auth."), int, "auth.salt_bytes")
    _require_type(_require_key(auth, "token_secret", "auth."), str, "auth.token_secret")
    _require_type(_require_key(auth, "token_ttl_seconds", "auth."), int, "auth.token_ttl_seconds")

    _require_type(_require_key(pagination, "default_page_size", "pagination."), int, "pagination.default_page_size")
    _require_type(_require_key(pagination, "max_page_size", "pagination."), int, "pagination.max_page_size")

    _require_type(_require_key(locks, "default_ttl_seconds", "locks."), int, "locks.default_ttl_seconds")
    _require_type(_require_key(cors, "allow_origins", "cors."), list, "cors.allow_origins")
    _require_type(_require_key(cors, "allow_methods", "cors."), list, "cors.allow_methods")
    _require_type(_require_key(cors, "allow_headers", "cors."), list, "cors.allow_headers")
    _require_type(_require_key(cors, "expose_headers", "cors."), list, "cors.expose_headers")
    _require_type(_require_key(cors, "allow_credentials", "cors."), bool, "cors.allow_credentials")
    _require_type(_require_key(cors, "max_age", "cors."), int, "cors.max_age")
    _require_type(_require_key(http, "gzip_minimum_size", "http."), int, "http.gzip_minimum_size")
    _require_type(_require_key(text_list, "max_text_length", "text_list."), int, "text_list.max_text_length")

    maintenance_enabled = _parse_bool(_require_key(maintenance, "enabled", "maintenance."), "maintenance.enabled")
    maintenance_message = _require_type(_require_key(maintenance, "message", "maintenance."), str, "maintenance.message")
    maintenance_allow_paths = _require_type(
        _require_key(maintenance, "allow_paths", "maintenance."),
        list,
        "maintenance.allow_paths",
    )
    for idx, item in enumerate(maintenance_allow_paths):
        _require_type(item, str, f"maintenance.allow_paths[{idx}]")

    maintenance["enabled"] = maintenance_enabled
    maintenance["message"] = maintenance_message
    maintenance["allow_paths"] = maintenance_allow_paths

    return data


_CONFIG_CACHE: Optional[Dict[str, Any]] = None


def get_config() -> Dict[str, Any]:
    global _CONFIG_CACHE
    if _CONFIG_CACHE is None:
        _CONFIG_CACHE = load_config()
    return _CONFIG_CACHE
