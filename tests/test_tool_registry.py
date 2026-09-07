"""Tests for the automatic tool registry in agent.tools."""

from agent.tools import TOOLS, get_tools

EXPECTED_TOOLS = {
    "calculator",
    "get_current_datetime",
    "get_weather",
    "wikipedia_search",
    "web_search",
    "submit_calculation",
    "unit_converter",
    "read_file",
    "write_file",
    "list_files",
    "delete_file",
}


def test_registry_contains_all_tools() -> None:
    """Every @tool-decorated function is auto-registered."""
    assert {t.name for t in get_tools()} == EXPECTED_TOOLS


def test_no_duplicate_registration() -> None:
    names = [t.name for t in get_tools()]
    assert len(names) == len(set(names))


def test_tools_alias_matches_registry() -> None:
    """The module-level TOOLS convenience alias stays in sync with get_tools()."""
    assert [t.name for t in TOOLS] == [t.name for t in get_tools()]


def test_tool_descriptions_are_meaningful() -> None:
    """Descriptions come from each function's docstring, not the generic
    StructuredTool class docstring."""
    for t in get_tools():
        assert t.description and t.description.strip()
        assert "any number of inputs" not in t.description
