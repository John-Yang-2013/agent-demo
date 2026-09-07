"""Structured output: submit_calculation tool + CalculationResult schema."""

import pytest
from pydantic import ValidationError

from agent import tools
from agent.schemas import CalculationResult


def test_valid_submission_accepted() -> None:
    tools._LAST_STRUCTURED.clear()
    out = tools.submit_calculation.invoke(
        {
            "expression": "2 ** 10",
            "value": 1024,
            "explanation": "2 to the 10th power",
        }
    )
    assert "accepted" in out
    stored = tools.get_last_structured()
    assert stored is not None
    assert stored.value == 1024
    assert stored.category == "calculation"
    assert stored.unit is None


def test_conversion_with_unit() -> None:
    tools._LAST_STRUCTURED.clear()
    tools.submit_calculation.invoke(
        {
            "expression": "100 mph -> kph",
            "value": 160.934,
            "unit": "kph",
            "category": "conversion",
            "explanation": "100 miles per hour in km/h",
        }
    )
    stored = tools.get_last_structured()
    assert stored is not None
    assert stored.unit == "kph"
    assert stored.category == "conversion"


def test_invalid_category_rejected_and_self_correctable() -> None:
    tools._LAST_STRUCTURED.clear()
    out = tools.submit_calculation.invoke(
        {"expression": "1+1", "value": 2, "category": "measurement"}
    )
    # Rejected with guidance; nothing stored.
    assert "Invalid structured result" in out
    assert "category" in out
    assert tools.get_last_structured() is None


def test_numeric_string_value_coerced() -> None:
    out = tools.submit_calculation.invoke({"expression": "6*7", "value": "42"})
    assert "accepted" in out
    stored = tools.get_last_structured()
    assert stored is not None
    assert stored.value == 42.0


def test_schema_direct_validation() -> None:
    ok = CalculationResult(expression="1+1", value=2)
    assert ok.category == "calculation"
    assert ok.unit is None
    with pytest.raises(ValidationError):
        CalculationResult(expression="1+1", value="not-a-number")
