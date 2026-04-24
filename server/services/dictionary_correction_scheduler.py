# 词典系统纠错定时调度。
from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Optional

from loguru import logger

from ..config import get_config
from . import dictionary_correction

_scheduler_task: Optional[asyncio.Task] = None


async def _run_loop() -> None:
    config = get_config()["dictionary_correction"]
    interval_seconds = int(config["scan_interval_seconds"])
    batch_size = int(config["batch_size"])
    lock_name = str(config["lock_name"])

    logger.info(
        "dictionary correction scheduler started: intervalSeconds={} batchSize={} lockName={}",
        interval_seconds,
        batch_size,
        lock_name,
    )
    while True:
        try:
            lock_connection = dictionary_correction.acquire_correction_lock(lock_name)
            if lock_connection is not None:
                try:
                    entry_ids = dictionary_correction.fetch_pending_dictionary_ids(batch_size)
                    for entry_id in entry_ids:
                        try:
                            dictionary_correction.run_dictionary_correction(entry_id)
                        except Exception as error:
                            dictionary_correction.mark_dictionary_correction_failed(entry_id, str(error))
                            logger.exception("scheduled dictionary correction failed: entryId={} error={}", entry_id, error)
                finally:
                    dictionary_correction.release_correction_lock(lock_name, lock_connection)
            else:
                logger.debug("dictionary correction scheduler skipped: lock not acquired")
        except asyncio.CancelledError:
            raise
        except Exception as error:
            logger.exception("dictionary correction scheduler loop failed: {}", error)

        await asyncio.sleep(interval_seconds)


def start_scheduler() -> None:
    global _scheduler_task
    config = get_config()["dictionary_correction"]
    if not config["enabled"]:
        logger.info("dictionary correction scheduler disabled by config")
        return
    if _scheduler_task is not None and not _scheduler_task.done():
        return
    _scheduler_task = asyncio.create_task(_run_loop(), name="dictionary-correction-scheduler")


async def stop_scheduler() -> None:
    global _scheduler_task
    if _scheduler_task is None:
        return
    _scheduler_task.cancel()
    with suppress(asyncio.CancelledError):
        await _scheduler_task
    _scheduler_task = None
