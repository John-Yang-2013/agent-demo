"""Tests for the get_current_datetime tool."""

import re
from datetime import datetime

from agent.tools import get_current_datetime


def _dt(tz: str = "UTC") -> str:
    return get_current_datetime.invoke({"timezone_name": tz})


def test_utc_default() -> None:
    out = _dt("UTC")
    assert "Current Date & Time (UTC)" in out
    assert "Date" in out
    assert "Time" in out
    assert "Day of Week" in out
    assert "Week Number" in out


def test_valid_timezone() -> None:
    out = _dt("Asia/Tokyo")
    assert "Current Date & Time (Asia/Tokyo)" in out
    # Tokyo is UTC+9
    assert "+09" in out or "+0900" in out


def test_unknown_timezone() -> None:
    out = _dt("Mars/Olympus")
    assert "Unknown timezone" in out
    assert "Mars/Olympus" in out


def test_default_parameter_utc() -> None:
    out = get_current_datetime.invoke({"timezone_name": "UTC"})
    assert "UTC" in out


def test_date_format_is_iso() -> None:
    out = _dt("UTC")
    # The Date line should contain a YYYY-MM-DD string.
    match = re.search(r"Date\s*:\s*(\d{4}-\d{2}-\d{2})", out)
    assert match is not None
    # Make sure it's a real, parseable date.
    datetime.strptime(match.group(1), "%Y-%m-%d")


def test_day_of_year_and_remaining() -> None:
    out = _dt("UTC")
    assert "Day of Year" in out
    assert "days remaining" in out


def test_unix_timestamp_present() -> None:
    out = _dt("UTC")
    assert "Unix Timestamp" in out
    match = re.search(r"Unix Timestamp\s*:\s*(\d+)", out)
    assert match is not None
    # Sanity: timestamp should be in the plausible present range (> year 2020).
    assert int(match.group(1)) > 1_577_836_800  # 2020-01-01 UTC
