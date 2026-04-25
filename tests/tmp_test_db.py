import pytest

from server.db import DatabaseConfigError, _tinyint_to_bool

pytestmark = pytest.mark.no_db


def test_tinyint_to_bool_supports_common_true_values():
    assert _tinyint_to_bool(1) is True
    assert _tinyint_to_bool("1") is True
    assert _tinyint_to_bool(b"1") is True
    assert _tinyint_to_bool(True) is True


def test_tinyint_to_bool_supports_common_false_values():
    assert _tinyint_to_bool(0) is False
    assert _tinyint_to_bool("0") is False
    assert _tinyint_to_bool(b"0") is False
    assert _tinyint_to_bool(False) is False


def test_tinyint_to_bool_rejects_invalid_value():
    with pytest.raises(DatabaseConfigError, match="TINYINT 布尔值非法"):
        _tinyint_to_bool("2")


def test_tinyint_to_bool_rejects_invalid_type():
    with pytest.raises(DatabaseConfigError, match="TINYINT 布尔值类型非法"):
        _tinyint_to_bool([])
