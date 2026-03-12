# 日志配置（loguru）。
import sys
from pathlib import Path

from loguru import logger


def setup_logger() -> None:
    logger.remove()

    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level:<8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "{message}"
    )
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "{level:<8} | "
        "{name}:{function}:{line} | "
        "{message}"
    )

    logger.add(sys.stdout, format=log_format, level="INFO", colorize=True)

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    logger.add(
        log_dir / "server.log",
        format=file_format,
        level="INFO",
        rotation="10 MB",
        retention="30 days",
        encoding="utf-8",
    )
