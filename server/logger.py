# 日志配置（loguru）。
import sys
from pathlib import Path

from loguru import logger

from .logging_context import get_log_context


def _patch_record(record):
    record["extra"].update(get_log_context())


def setup_logger() -> None:
    logger.remove()
    logger.configure(patcher=_patch_record)

    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level:<8}</level> | "
        "req=<magenta>{extra[requestId]}</magenta> "
        "user=<yellow>{extra[userId]}</yellow>/<yellow>{extra[username]}</yellow> "
        "ip=<cyan>{extra[clientIp]}</cyan> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "{message}"
    )
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "{level:<8} | "
        "req={extra[requestId]} user={extra[userId]}/{extra[username]} ip={extra[clientIp]} | "
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
