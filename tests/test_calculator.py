"""Tests for the calculator tool — arithmetic, math functions, and security.

The calculator is an AST-based safe evaluator; these tests also act as a
security regression suite for the sandbox (no attribute access, no builtins,
no imports).
"""

from agent.tools import calculator


def _calc(expr: str) -> str:
    """Invoke the calculator tool with a single expression and return its string output."""
    return calculator.invoke({"expression": expr})


# --------------------------------------------------------------------------- #
# Basic arithmetic
# --------------------------------------------------------------------------- #


def test_addition() -> None:
    assert _calc("2 + 2") == "2 + 2 = 4"


def test_subtraction() -> None:
    assert _calc("10 - 4") == "10 - 4 = 6"


def test_multiplication() -> None:
    assert _calc("6 * 7") == "6 * 7 = 42"


def test_division_float() -> None:
    out = _calc("7 / 2")
    assert "3.5" in out


def test_floor_division() -> None:
    assert _calc("7 // 2") == "7 // 2 = 3"


def test_modulo() -> None:
    assert _calc("10 % 3") == "10 % 3 = 1"


def test_power() -> None:
    assert _calc("2 ** 10") == "2 ** 10 = 1024"


def test_integer_result_float_display() -> None:
    """A float that is a whole number should render without trailing .0."""
    assert _calc("sqrt(144)") == "sqrt(144) = 12"


def test_operator_precedence() -> None:
    assert _calc("2 + 3 * 4") == "2 + 3 * 4 = 14"


def test_parentheses() -> None:
    assert _calc("(2 + 3) * 4") == "(2 + 3) * 4 = 20"


def test_unary_minus() -> None:
    out = _calc("-5 + 3")
    assert "-2" in out


# --------------------------------------------------------------------------- #
# Math functions & constants
# --------------------------------------------------------------------------- #


def test_sqrt() -> None:
    assert _calc("sqrt(16)") == "sqrt(16) = 4"


def test_log10() -> None:
    assert _calc("log10(1000)") == "log10(1000) = 3"


def test_log2() -> None:
    assert _calc("log2(8)") == "log2(8) = 3"


def test_exp() -> None:
    out = _calc("exp(0)")
    assert "1" in out


def test_abs() -> None:
    assert _calc("abs(-42)") == "abs(-42) = 42"


def test_ceil_floor_round() -> None:
    assert _calc("ceil(2.3)") == "ceil(2.3) = 3"
    assert _calc("floor(2.9)") == "floor(2.9) = 2"
    assert _calc("round(2.567, 2)") == "round(2.567, 2) = 2.57"


def test_constants() -> None:
    out = _calc("pi")
    # calculator formats floats with %.10g, so only ~10 sig figs are shown.
    assert "3.14159265" in out
    out_e = _calc("e")
    assert "2.718" in out_e


def test_compound_expression() -> None:
    out = _calc("sqrt(144) + log10(1000)")
    assert "15" in out


# --------------------------------------------------------------------------- #
# Errors
# --------------------------------------------------------------------------- #


def test_division_by_zero() -> None:
    out = _calc("1 / 0")
    assert "Division by zero" in out


def test_unknown_name() -> None:
    out = _calc("foo + 1")
    assert "Error" in out and "foo" in out


def test_syntax_error() -> None:
    out = _calc("2 +")
    assert "Error" in out


def test_empty_expression() -> None:
    out = _calc("   ")
    assert "Error" in out


# --------------------------------------------------------------------------- #
# Security — the sandbox must reject attribute access, builtins, imports
# --------------------------------------------------------------------------- #


def test_no_attribute_access() -> None:
    out = _calc("(1).__class__")
    assert "Error" in out


def test_no_builtins_import() -> None:
    out = _calc("__import__('os')")
    # The sandbox must reject it (it never executes the import).
    assert "Error" in out
    # And must not claim success / leak the os module object.
    assert "<module 'os'" not in out


def test_no_open() -> None:
    out = _calc("open('/etc/passwd')")
    assert "Error" in out


def test_no_eval_or_exec() -> None:
    out = _calc("eval('1+1')")
    assert "Error" in out


def test_no_subscript_on_names() -> None:
    out = _calc("__builtins__['eval']")
    assert "Error" in out


def test_no_lambda() -> None:
    out = _calc("(lambda: 1)()")
    assert "Error" in out
