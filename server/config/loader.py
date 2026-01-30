# 配置文件加载与校验。
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv


_REQUIRED_TOP_LEVEL_KEYS = ("database", "auth", "pagination", "locks")
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

    _require_type(_require_key(database, "dsn", "database."), str, "database.dsn")

    _require_type(_require_key(auth, "hash_algorithm", "auth."), str, "auth.hash_algorithm")
    _require_type(_require_key(auth, "salt_bytes", "auth."), int, "auth.salt_bytes")
    _require_type(_require_key(auth, "token_secret", "auth."), str, "auth.token_secret")
    _require_type(_require_key(auth, "token_ttl_seconds", "auth."), int, "auth.token_ttl_seconds")

    _require_type(_require_key(pagination, "default_page_size", "pagination."), int, "pagination.default_page_size")
    _require_type(_require_key(pagination, "max_page_size", "pagination."), int, "pagination.max_page_size")

    _require_type(_require_key(locks, "default_ttl_seconds", "locks."), int, "locks.default_ttl_seconds")

    return data


_CONFIG_CACHE: Optional[Dict[str, Any]] = None


def get_config() -> Dict[str, Any]:
    global _CONFIG_CACHE
    if _CONFIG_CACHE is None:
        _CONFIG_CACHE = load_config()
    return _CONFIG_CACHE
