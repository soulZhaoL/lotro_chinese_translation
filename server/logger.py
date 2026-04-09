# 日志配置（loguru）。
import sys
from datetime import date, datetime
from pathlib import Path

from loguru import logger

from .logging_context import get_log_context

_LOG_FILE_ROTATION_SIZE_BYTES = 20 * 1024 * 1024


def _patch_record(record):
    record["extra"].update(get_log_context())


def _get_log_file_date(file) -> date | None:
    try:
        return datetime.fromtimestamp(Path(file.name).stat().st_mtime).date()
    except (OSError, ValueError):
        return None


class DailyOrSizeRotation:
    def __init__(self, max_bytes: int):
        self.max_bytes = max_bytes
        self._current_date: date | None = None

    def __call__(self, message, file) -> bool:
        message_date = message.record["time"].date()
        if self._current_date is None:
            self._current_date = _get_log_file_date(file) or message_date

        if message_date != self._current_date:
            self._current_date = message_date
            return True

        file.seek(0, 2)
        pending_bytes = len(str(message).encode("utf-8"))
        return file.tell() + pending_bytes > self.max_bytes


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
        rotation=DailyOrSizeRotation(_LOG_FILE_ROTATION_SIZE_BYTES),
        retention="30 days",
        encoding="utf-8",
    )
