from datetime import datetime, timezone

from utils.clock import utcnow_aware, utcnow_naive


def test_utcnow_naive_is_naive_utc_datetime():
    value = utcnow_naive()
    assert isinstance(value, datetime)
    assert value.tzinfo is None


def test_utcnow_aware_has_utc_timezone():
    value = utcnow_aware()
    assert isinstance(value, datetime)
    assert value.tzinfo is not None
    assert value.utcoffset() == timezone.utc.utcoffset(value)
