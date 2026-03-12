"""
Tool definitions for the AI agent.

Tools:
  - calculator       — safe arithmetic / math-function evaluator
  - get_current_datetime — date, time, timezone, countdown helpers
  - get_weather      — real-time weather via wttr.in (no API key)
  - wikipedia_search — Wikipedia article summary lookup
  - unit_converter   — length, weight, temp, speed, area, volume, data, time
"""

import ast
import math
import operator
from datetime import datetime, timezone
from urllib.parse import quote

import requests
from langchain_core.tools import tool


# ---------------------------------------------------------------------------
# 1. Calculator — safe expression evaluator
# ---------------------------------------------------------------------------

_BINARY_OPS: dict = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}

_UNARY_OPS: dict = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

_SAFE_NAMES: dict = {
    "sqrt": math.sqrt,
    "cbrt": lambda x: x ** (1 / 3),
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "log": math.log,
    "log2": math.log2,
    "log10": math.log10,
    "exp": math.exp,
    "abs": abs,
    "ceil": math.ceil,
    "floor": math.floor,
    "round": round,
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
    "inf": math.inf,
}


def _safe_eval_node(node: ast.expr):
    if isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float, complex)):
            raise ValueError(f"Unsupported literal type: {type(node.value).__name__}")
        return node.value
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _BINARY_OPS:
            raise ValueError(f"Unsupported operator: {op_type.__name__}")
        left = _safe_eval_node(node.left)
        right = _safe_eval_node(node.right)
        return _BINARY_OPS[op_type](left, right)
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _UNARY_OPS:
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
        return _UNARY_OPS[op_type](_safe_eval_node(node.operand))
    elif isinstance(node, ast.Name):
        if node.id not in _SAFE_NAMES:
            raise ValueError(f"Unknown name: '{node.id}'")
        return _SAFE_NAMES[node.id]
    elif isinstance(node, ast.Call):
        func = _safe_eval_node(node.func)
        if not callable(func):
            raise ValueError(f"'{node.func}' is not callable")
        args = [_safe_eval_node(a) for a in node.args]
        return func(*args)
    else:
        raise ValueError(f"Unsupported expression type: {type(node).__name__}")


@tool
def calculator(expression: str) -> str:
    """
    Evaluate a mathematical expression safely.

    Supports arithmetic: +, -, *, /, ** (power), % (modulo), // (floor division).
    Supports functions: sqrt, cbrt, sin, cos, tan, asin, acos, atan,
                        log, log2, log10, exp, abs, ceil, floor, round.
    Constants: pi, e, tau, inf.

    Examples:
      "2 ** 10"                   → 1024
      "sqrt(144) + log10(1000)"  → 15.0
      "round(sin(pi/6), 4)"      → 0.5
      "(100 * 1.065) ** 5"       → compound growth
    """
    try:
        expr = expression.strip()
        tree = ast.parse(expr, mode="eval")
        result = _safe_eval_node(tree.body)
        if isinstance(result, float):
            if result.is_integer() and abs(result) < 1e15:
                return f"{expr} = {int(result)}"
            return f"{expr} = {result:.10g}"
        return f"{expr} = {result}"
    except ZeroDivisionError:
        return f"Error: Division by zero in '{expression}'"
    except Exception as exc:
        return f"Error evaluating '{expression}': {exc}"


# ---------------------------------------------------------------------------
# 2. Date / Time
# ---------------------------------------------------------------------------

@tool
def get_current_datetime(timezone_name: str = "UTC") -> str:
    """
    Get the current date and time information.

    Args:
        timezone_name: IANA timezone name, e.g. 'UTC', 'US/Eastern', 'Asia/Tokyo',
                       'Europe/London', 'Australia/Sydney'.  Defaults to 'UTC'.

    Returns rich date/time info including day-of-week, week number, and day-of-year.
    """
    try:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
        try:
            tz = ZoneInfo(timezone_name)
        except (ZoneInfoNotFoundError, KeyError):
            return f"Unknown timezone '{timezone_name}'. Use IANA names like 'US/Eastern' or 'Asia/Tokyo'."

        now = datetime.now(tz)
        day_of_year = now.timetuple().tm_yday
        days_in_year = 366 if (now.year % 4 == 0 and (now.year % 100 != 0 or now.year % 400 == 0)) else 365
        days_remaining = days_in_year - day_of_year
        week_num = now.isocalendar()[1]

        return (
            f"Current Date & Time ({timezone_name}):\n"
            f"  Date        : {now.strftime('%Y-%m-%d')} ({now.strftime('%B %d, %Y')})\n"
            f"  Time        : {now.strftime('%H:%M:%S')}\n"
            f"  Day of Week : {now.strftime('%A')}\n"
            f"  Week Number : {week_num}\n"
            f"  Day of Year : {day_of_year} / {days_in_year} ({days_remaining} days remaining)\n"
            f"  UTC Offset  : {now.strftime('%z')}\n"
            f"  Unix Timestamp: {int(now.timestamp())}"
        )
    except Exception as exc:
        now = datetime.now(timezone.utc)
        return f"Current UTC time: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC  (fallback — error: {exc})"


# ---------------------------------------------------------------------------
# 3. Weather — wttr.in JSON API (no key required)
# ---------------------------------------------------------------------------

@tool
def get_weather(location: str) -> str:
    """
    Fetch current weather conditions for any city or location worldwide.

    Input: city name or location string, e.g. 'Tokyo', 'New York', 'London, UK',
           'Sydney, Australia', or GPS coordinates like '35.6762,139.6503'.

    Returns temperature (°C / °F), feels-like, conditions, humidity,
    wind speed & direction, visibility, and UV index.
    """
    try:
        url = f"https://wttr.in/{quote(location)}?format=j1"
        headers = {"User-Agent": "AgentDemo/1.0 (github.com/ai-agent-demo)"}
        response = requests.get(url, headers=headers, timeout=12)
        response.raise_for_status()
        data = response.json()

        current = data["current_condition"][0]
        nearest = data["nearest_area"][0]

        city = nearest["areaName"][0]["value"]
        region = nearest.get("region", [{"value": ""}])[0]["value"]
        country = nearest["country"][0]["value"]
        location_str = f"{city}, {region}, {country}".replace(", ,", ",").strip(", ")

        temp_c = current["temp_C"]
        temp_f = current["temp_F"]
        feels_c = current["FeelsLikeC"]
        feels_f = current["FeelsLikeF"]
        description = current["weatherDesc"][0]["value"]
        humidity = current["humidity"]
        wind_kmph = current["windspeedKmph"]
        wind_mph = current["windspeedMiles"]
        wind_dir = current["winddir16Point"]
        visibility_km = current["visibility"]
        uv_index = current["uvIndex"]
        pressure = current["pressure"]
        precip_mm = current["precipMM"]

        # Tomorrow's forecast for context
        forecast_lines = ""
        if "weather" in data and len(data["weather"]) > 1:
            tmr = data["weather"][1]
            tmr_desc = tmr["hourly"][4]["weatherDesc"][0]["value"] if tmr.get("hourly") else "N/A"
            forecast_lines = (
                f"\nTomorrow's Forecast:\n"
                f"  High / Low  : {tmr['maxtempC']}°C / {tmr['mintempC']}°C "
                f"({tmr['maxtempF']}°F / {tmr['mintempF']}°F)\n"
                f"  Expected    : {tmr_desc}"
            )

        return (
            f"Weather in {location_str}:\n"
            f"  Conditions  : {description}\n"
            f"  Temperature : {temp_c}°C / {temp_f}°F\n"
            f"  Feels Like  : {feels_c}°C / {feels_f}°F\n"
            f"  Humidity    : {humidity}%\n"
            f"  Wind        : {wind_kmph} km/h ({wind_mph} mph) {wind_dir}\n"
            f"  Visibility  : {visibility_km} km\n"
            f"  Pressure    : {pressure} hPa\n"
            f"  Precip.     : {precip_mm} mm\n"
            f"  UV Index    : {uv_index}"
            f"{forecast_lines}"
        )
    except requests.Timeout:
        return f"Weather service timed out for '{location}'. Try again or check your connection."
    except requests.HTTPError as exc:
        return f"Weather API error for '{location}': {exc}"
    except Exception as exc:
        return f"Could not fetch weather for '{location}': {exc}"


# ---------------------------------------------------------------------------
# 4. Wikipedia Search
# ---------------------------------------------------------------------------

@tool
def wikipedia_search(query: str) -> str:
    """
    Search Wikipedia and return a concise article summary.

    Best for: factual questions, historical events, scientific concepts, people,
    places, technology, culture, and any general knowledge topic.

    Input: a topic name or natural-language query.
    Returns: article title, 5-sentence summary, and source URL.
    """
    try:
        import wikipedia as wiki

        wiki.set_lang("en")
        search_results = wiki.search(query, results=5)
        if not search_results:
            return f"No Wikipedia articles found for '{query}'."

        for title in search_results[:3]:
            try:
                page = wiki.page(title, auto_suggest=False)
                summary = wiki.summary(title, sentences=6, auto_suggest=False)
                return (
                    f"**{page.title}**\n\n"
                    f"{summary}\n\n"
                    f"Source: {page.url}"
                )
            except wiki.DisambiguationError as exc:
                # Try the first disambiguation option
                if exc.options:
                    try:
                        page = wiki.page(exc.options[0], auto_suggest=False)
                        summary = wiki.summary(exc.options[0], sentences=6, auto_suggest=False)
                        return (
                            f"**{page.title}** (disambiguation resolved)\n\n"
                            f"{summary}\n\n"
                            f"Source: {page.url}"
                        )
                    except Exception:
                        continue
            except wiki.PageError:
                continue
            except Exception:
                continue

        return f"Could not retrieve a Wikipedia article for '{query}'. Tried: {', '.join(search_results[:3])}."
    except ImportError:
        return "Wikipedia package not installed. Run: pip install wikipedia"
    except Exception as exc:
        return f"Wikipedia search error: {exc}"


# ---------------------------------------------------------------------------
# 5. Unit Converter
# ---------------------------------------------------------------------------

# Conversion tables — all values are multipliers to the SI base unit.
_LENGTH = {   # base: metre
    "mm": 1e-3, "cm": 1e-2, "m": 1, "km": 1e3,
    "inch": 0.0254, "in": 0.0254, "inches": 0.0254,
    "foot": 0.3048, "ft": 0.3048, "feet": 0.3048,
    "yard": 0.9144, "yd": 0.9144, "yards": 0.9144,
    "mile": 1609.344, "mi": 1609.344, "miles": 1609.344,
    "nautical_mile": 1852, "nmi": 1852,
    "light_year": 9.4607e15, "ly": 9.4607e15,
    "au": 1.496e11,  # astronomical unit
}

_WEIGHT = {   # base: kilogram
    "mg": 1e-6, "g": 1e-3, "kg": 1, "tonne": 1e3, "t": 1e3,
    "ounce": 0.0283495, "oz": 0.0283495,
    "pound": 0.453592, "lb": 0.453592, "lbs": 0.453592, "pounds": 0.453592,
    "stone": 6.35029, "st": 6.35029,
    "ton": 907.185,  # US short ton
}

_SPEED = {    # base: m/s
    "mps": 1, "m/s": 1,
    "kph": 1 / 3.6, "km/h": 1 / 3.6, "kmh": 1 / 3.6,
    "mph": 0.44704,
    "knot": 0.514444, "kn": 0.514444, "knots": 0.514444,
    "fps": 0.3048,  # feet per second
    "mach": 340.29,
}

_AREA = {     # base: m²
    "sq_m": 1, "m2": 1,
    "sq_km": 1e6, "km2": 1e6,
    "sq_cm": 1e-4, "cm2": 1e-4,
    "sq_ft": 0.092903, "ft2": 0.092903,
    "sq_yd": 0.836127, "yd2": 0.836127,
    "sq_mile": 2.58999e6, "mi2": 2.58999e6,
    "hectare": 1e4, "ha": 1e4,
    "acre": 4046.86,
}

_VOLUME = {   # base: litre
    "ml": 0.001, "l": 1, "liter": 1, "litre": 1,
    "cl": 0.01, "dl": 0.1,
    "gallon": 3.78541, "gallon_us": 3.78541, "gal": 3.78541,
    "gallon_uk": 4.54609,
    "cup": 0.236588,
    "pint": 0.473176, "pint_us": 0.473176, "pt": 0.473176,
    "quart": 0.946353, "quart_us": 0.946353, "qt": 0.946353,
    "fl_oz": 0.0295735, "fluid_oz": 0.0295735,
    "tbsp": 0.0147868, "tsp": 0.00492892,
    "cubic_m": 1000, "m3": 1000,
}

_DATA = {     # base: byte
    "bit": 0.125,
    "byte": 1, "b": 1,
    "kb": 1024, "kilobyte": 1024,
    "mb": 1024 ** 2, "megabyte": 1024 ** 2,
    "gb": 1024 ** 3, "gigabyte": 1024 ** 3,
    "tb": 1024 ** 4, "terabyte": 1024 ** 4,
    "pb": 1024 ** 5, "petabyte": 1024 ** 5,
    "kib": 1024, "mib": 1024 ** 2, "gib": 1024 ** 3, "tib": 1024 ** 4,
}

_TIME = {     # base: second
    "ns": 1e-9, "nanosecond": 1e-9,
    "us": 1e-6, "microsecond": 1e-6,
    "ms": 1e-3, "millisecond": 1e-3,
    "s": 1, "second": 1, "sec": 1, "seconds": 1,
    "min": 60, "minute": 60, "minutes": 60,
    "h": 3600, "hr": 3600, "hour": 3600, "hours": 3600,
    "d": 86400, "day": 86400, "days": 86400,
    "week": 604800, "wk": 604800,
    "month": 2628000,   # avg 30.4375 days
    "year": 31557600,   # Julian year
    "yr": 31557600,
    "decade": 315576000,
    "century": 3155760000,
}

_CATEGORIES = [
    (_LENGTH, "length", "metre"),
    (_WEIGHT, "mass", "kilogram"),
    (_SPEED, "speed", "m/s"),
    (_AREA, "area", "m²"),
    (_VOLUME, "volume", "litre"),
    (_DATA, "digital storage", "byte"),
    (_TIME, "time", "second"),
]

_TEMP_UNITS = {"celsius", "c", "fahrenheit", "f", "kelvin", "k", "rankine", "r"}


def _format_number(value: float) -> str:
    if value == 0:
        return "0"
    abs_val = abs(value)
    if abs_val >= 1e12 or (abs_val < 1e-4 and abs_val > 0):
        return f"{value:.6e}"
    return f"{value:,.10g}"


@tool
def unit_converter(value: float, from_unit: str, to_unit: str) -> str:
    """
    Convert a numeric value between units.

    Supported categories:
      Length     : mm, cm, m, km, inch/in, foot/ft, yard/yd, mile/mi,
                   nautical_mile/nmi, light_year/ly, au
      Mass       : mg, g, kg, tonne, ounce/oz, pound/lb, stone, ton
      Speed      : mps (m/s), kph/km/h, mph, knot/kn, fps, mach
      Area       : sq_m/m2, sq_km/km2, sq_ft, sq_mile, hectare/ha, acre
      Volume     : ml, l, gallon, cup, pint, quart, fl_oz, cubic_m
      Data       : bit, byte, kb, mb, gb, tb, pb
      Time       : ns, ms, s/second, min/minute, h/hour, d/day, week, month, year
      Temperature: celsius/c, fahrenheit/f, kelvin/k, rankine/r

    Args:
        value: the numeric amount to convert
        from_unit: source unit (case-insensitive)
        to_unit: target unit (case-insensitive)

    Example: value=100, from_unit="mph", to_unit="kph"
    """
    fu = from_unit.lower().strip().replace(" ", "_").replace("-", "_")
    tu = to_unit.lower().strip().replace(" ", "_").replace("-", "_")

    # --- Temperature (non-linear, special case) ---
    if fu in _TEMP_UNITS and tu in _TEMP_UNITS:
        # Normalise to first letter: c / f / k / r
        fc = fu[0]
        tc = tu[0]

        # To Celsius
        if fc == "c":
            celsius = value
        elif fc == "f":
            celsius = (value - 32) * 5 / 9
        elif fc == "k":
            celsius = value - 273.15
        elif fc == "r":
            celsius = (value - 491.67) * 5 / 9
        else:
            return f"Unknown temperature unit '{from_unit}'."

        # From Celsius to target
        if tc == "c":
            result = celsius
        elif tc == "f":
            result = celsius * 9 / 5 + 32
        elif tc == "k":
            result = celsius + 273.15
        elif tc == "r":
            result = (celsius + 273.15) * 9 / 5
        else:
            return f"Unknown temperature unit '{to_unit}'."

        return f"{_format_number(value)} {from_unit} = {_format_number(result)} {to_unit}  (temperature)"

    # --- Linear categories ---
    for table, category, base_unit in _CATEGORIES:
        if fu in table and tu in table:
            base_value = value * table[fu]
            result = base_value / table[tu]
            return (
                f"{_format_number(value)} {from_unit} = {_format_number(result)} {to_unit}  ({category})"
            )

    # Units found in different categories?
    from_cat = next((cat for tbl, cat, _ in _CATEGORIES if fu in tbl), None)
    to_cat = next((cat for tbl, cat, _ in _CATEGORIES if tu in tbl), None)

    if from_cat and to_cat and from_cat != to_cat:
        return f"Cannot convert '{from_unit}' ({from_cat}) to '{to_unit}' ({to_cat}) — incompatible dimensions."
    return (
        f"Unknown unit(s): '{from_unit}' or '{to_unit}'. "
        "Check the spelling or refer to the supported units list."
    )


TOOLS = [calculator, get_current_datetime, get_weather, wikipedia_search, unit_converter]
