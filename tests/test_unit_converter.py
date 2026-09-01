"""Tests for the unit_converter tool across every supported category."""

import pytest

from agent.tools import unit_converter


def _conv(value: float, from_unit: str, to_unit: str) -> str:
    return unit_converter.invoke({"value": value, "from_unit": from_unit, "to_unit": to_unit})


def _extract_result_number(out: str) -> float:
    """Pull the numeric result out of a 'X from = Y to  (category)' string."""
    # Format: "<value> <from> = <result> <to>  (category)"
    rhs = out.split("=", 1)[1]
    number_str = rhs.split()[0].replace(",", "")
    return float(number_str)


# --------------------------------------------------------------------------- #
# Length
# --------------------------------------------------------------------------- #


def test_km_to_miles() -> None:
    out = _conv(100, "km", "miles")
    assert _extract_result_number(out) == pytest.approx(62.137, rel=1e-3)


def test_mile_to_km() -> None:
    out = _conv(1, "mile", "km")
    assert _extract_result_number(out) == pytest.approx(1.609344)


def test_inch_aliases() -> None:
    assert _extract_result_number(_conv(12, "inch", "cm")) == pytest.approx(30.48)
    assert _extract_result_number(_conv(12, "in", "cm")) == pytest.approx(30.48)
    assert _extract_result_number(_conv(12, "inches", "cm")) == pytest.approx(30.48)


# --------------------------------------------------------------------------- #
# Mass
# --------------------------------------------------------------------------- #


def test_kg_to_pounds() -> None:
    out = _conv(70, "kg", "pounds")
    assert _extract_result_number(out) == pytest.approx(154.324, rel=1e-3)


def test_kg_to_stones() -> None:
    out = _conv(70, "kg", "stone")
    assert _extract_result_number(out) == pytest.approx(11.023, rel=1e-3)


# --------------------------------------------------------------------------- #
# Speed
# --------------------------------------------------------------------------- #


def test_mph_to_kph() -> None:
    out = _conv(100, "mph", "kph")
    assert _extract_result_number(out) == pytest.approx(160.934, rel=1e-3)


def test_mph_to_mps() -> None:
    out = _conv(100, "mph", "mps")
    assert _extract_result_number(out) == pytest.approx(44.704, rel=1e-3)


def test_knot_to_mph() -> None:
    out = _conv(1, "knot", "mph")
    assert _extract_result_number(out) == pytest.approx(1.15078, rel=1e-3)


# --------------------------------------------------------------------------- #
# Temperature (non-linear)
# --------------------------------------------------------------------------- #


def test_celsius_to_fahrenheit() -> None:
    out = _conv(37, "celsius", "fahrenheit")
    assert _extract_result_number(out) == pytest.approx(98.6, abs=0.1)


def test_fahrenheit_to_celsius() -> None:
    out = _conv(32, "fahrenheit", "celsius")
    assert _extract_result_number(out) == pytest.approx(0.0, abs=1e-6)


def test_celsius_to_kelvin() -> None:
    out = _conv(0, "celsius", "kelvin")
    assert _extract_result_number(out) == pytest.approx(273.15)


def test_kelvin_to_celsius() -> None:
    out = _conv(300, "kelvin", "celsius")
    assert _extract_result_number(out) == pytest.approx(26.85)


def test_fahrenheit_to_rankine() -> None:
    out = _conv(32, "fahrenheit", "rankine")
    assert _extract_result_number(out) == pytest.approx(491.67, abs=0.1)


def test_celsius_short_alias() -> None:
    out = _conv(100, "c", "f")
    assert _extract_result_number(out) == pytest.approx(212.0, abs=0.1)


# --------------------------------------------------------------------------- #
# Area, Volume, Data, Time
# --------------------------------------------------------------------------- #


def test_hectare_to_acre() -> None:
    out = _conv(1, "hectare", "acre")
    assert _extract_result_number(out) == pytest.approx(2.47105, rel=1e-3)


def test_gallon_to_litres() -> None:
    out = _conv(1, "gallon", "l")
    assert _extract_result_number(out) == pytest.approx(3.78541)


def test_gb_to_mb() -> None:
    out = _conv(1, "gb", "mb")
    assert _extract_result_number(out) == pytest.approx(1024.0)


def test_hour_to_seconds() -> None:
    out = _conv(14, "h", "s")
    assert _extract_result_number(out) == pytest.approx(50400.0)


def test_day_to_hours() -> None:
    out = _conv(1, "d", "h")
    assert _extract_result_number(out) == pytest.approx(24.0)


# --------------------------------------------------------------------------- #
# Error handling
# --------------------------------------------------------------------------- #


def test_incompatible_dimensions() -> None:
    out = _conv(1, "km", "kg")
    assert "incompatible" in out.lower() or "incompatible dimensions" in out.lower()


def test_unknown_unit() -> None:
    out = _conv(1, "floob", "bar")
    assert "Unknown" in out


def test_zero_value() -> None:
    out = _conv(0, "km", "m")
    assert _extract_result_number(out) == 0.0


def test_negative_value() -> None:
    out = _conv(-5, "celsius", "fahrenheit")
    assert _extract_result_number(out) == pytest.approx(23.0)
