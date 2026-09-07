"""Demo scenarios and help text for the interactive CLI."""

# --------------------------------------------------------------------------- #
# Demo scenarios — each showcases different tool(s)
# --------------------------------------------------------------------------- #

DEMO_SCENARIOS: list[dict] = [
    {
        "title": "🔢  Math & Compound Interest",
        "query": (
            "I invest $15,000 at 7% annual interest for 10 years. "
            "What is the final amount using compound interest (A = P * (1 + r)^t)? "
            "Also tell me the total profit."
        ),
        "highlight": "calculator",
    },
    {
        "title": "📅  Date & Countdown",
        "query": (
            "What is today's full date, day of the week, and week number? "
            "How many days are left in this year?"
        ),
        "highlight": "get_current_datetime",
    },
    {
        "title": "🌤  Live Weather Comparison",
        "query": (
            "Compare the current weather in Tokyo and London. "
            "Which city is warmer right now, and by how many degrees Celsius?"
        ),
        "highlight": "get_weather + calculator",
    },
    {
        "title": "📚  Knowledge Lookup",
        "query": "Explain quantum entanglement in simple terms. What makes it so remarkable?",
        "highlight": "wikipedia_search",
    },
    {
        "title": "📐  Unit Conversions",
        "query": (
            "Convert 100 miles per hour to km/h and m/s. "
            "Also convert 70 kg to pounds and stones. "
            "And what is 37°C in Fahrenheit?"
        ),
        "highlight": "unit_converter",
    },
    {
        "title": "🏃  Multi-Tool Challenge",
        "query": (
            "A marathon is 42.195 km. If I run at 12 km/h, how many minutes will it take? "
            "Convert that duration to hours:minutes and also to seconds. "
            "If I burn 70 kcal per km, what is my total calorie burn?"
        ),
        "highlight": "calculator + unit_converter",
    },
    {
        "title": "🌍  Travel Planner (all tools)",
        "query": (
            "I'm flying to Sydney, Australia tomorrow. "
            "What's the current weather there? "
            "The flight is 14 hours — convert that to minutes and seconds. "
            "If my destination is 11 hours ahead of UTC, what time will it be when I land "
            "(I'm departing at 08:00 UTC today)?"
        ),
        "highlight": "get_weather + get_current_datetime + unit_converter + calculator",
    },
]


# --------------------------------------------------------------------------- #
# Help text shown by the `help` command in interactive mode
# --------------------------------------------------------------------------- #

HELP_TEXT = """\
**Example queries**

| Category | Example |
|---|---|
| Math | `What is 15% of 847, rounded to 2 decimal places?` |
| Math | `Compound interest: $5000 at 8% for 3 years` |
| DateTime | `What day of the week is today? How many days until New Year?` |
| Weather | `What's the weather in Paris right now?` |
| Weather | `Compare weather in NYC and Tokyo` |
| Knowledge | `What is the Turing test?` |
| Units | `Convert 90 mph to km/h` |
| Units | `Convert 98.6°F to Celsius and Kelvin` |
| Multi | `A 10K race at 8 min/mile — how long in minutes and seconds?` |
| Memory | `What is 2^10?` then follow up: `now multiply that by 3` |

Type **demo** to run the showcase · **help** to see this · **clear** to reset history · **quit** to exit
"""
