from datetime import datetime, timedelta

import pytest

from server.logger import DailyOrSizeRotation


class _LogMessage(str):
    def __new__(cls, text: str, logged_at: datetime):
        message = str.__new__(cls, text)
        message.record = {"time": logged_at}
        return message


@pytest.mark.no_db
def test_daily_or_size_rotation_rotates_when_message_exceeds_size(tmp_path):
    log_path = tmp_path / "server.log"
    log_path.write_text("12345", encoding="utf-8")
    rotation = DailyOrSizeRotation(max_bytes=10)

    with log_path.open("r+", encoding="utf-8") as file:
        should_rotate = rotation(_LogMessage("123456", datetime.now()), file)

    assert should_rotate is True


@pytest.mark.no_db
def test_daily_or_size_rotation_keeps_file_when_same_day_and_under_size(tmp_path):
    log_path = tmp_path / "server.log"
    log_path.write_text("12345", encoding="utf-8")
    rotation = DailyOrSizeRotation(max_bytes=20)

    with log_path.open("r+", encoding="utf-8") as file:
        should_rotate = rotation(_LogMessage("12345", datetime.now()), file)

    assert should_rotate is False


@pytest.mark.no_db
def test_daily_or_size_rotation_rotates_when_log_day_changes(tmp_path):
    log_path = tmp_path / "server.log"
    log_path.write_text("12345", encoding="utf-8")
    rotation = DailyOrSizeRotation(max_bytes=100)
    first_log_time = datetime.now()
    next_day_log_time = first_log_time + timedelta(days=1)

    with log_path.open("r+", encoding="utf-8") as file:
        assert rotation(_LogMessage("first", first_log_time), file) is False
        assert rotation(_LogMessage("second", next_day_log_time), file) is True
