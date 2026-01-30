# 配置模块导出入口。
from .loader import ConfigError, get_config, load_config

__all__ = ["ConfigError", "get_config", "load_config"]
