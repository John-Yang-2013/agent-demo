"""Tests for <think>-tag filtering and the live token stream renderer."""

import io

from rich.console import Console

from agent.ui import LiveTokenStream, ThinkTagFilter

# --------------------------------------------------------------------------- #
# ThinkTagFilter — must stay consistent with strip_thinking()
# --------------------------------------------------------------------------- #


def test_plain_text_passes_through() -> None:
    f = ThinkTagFilter()
    out = f.feed("hello ") + f.feed("world") + f.flush()
    assert out == "hello world"


def test_whole_think_block_removed() -> None:
    f = ThinkTagFilter()
    assert f.feed("<think>secret</think>Answer!") + f.flush() == "Answer!"


def test_tag_split_across_chunks() -> None:
    f = ThinkTagFilter()
    parts = ["ans<thi", "nk>hidden</thi", "nk>done"]
    out = "".join(f.feed(p) for p in parts) + f.flush()
    assert out == "ansdone"


def test_char_by_char_feeding() -> None:
    """Any chunking of the raw stream must yield the same visible text."""
    raw = "a<think>b</think>c and <think>x</think>z!"
    f = ThinkTagFilter()
    assert "".join(f.feed(ch) for ch in raw) + f.flush() == "ac and z!"


def test_unclosed_think_dropped_at_flush() -> None:
    f = ThinkTagFilter()
    f.feed("<think>never closed, model cut off…")
    assert f.flush() == ""


def test_multiple_think_blocks() -> None:
    f = ThinkTagFilter()
    raw = "<think>a</think>1<think>b</think>2"
    assert "".join(f.feed(t) for t in raw.split("X")) + f.flush() == "12"


# --------------------------------------------------------------------------- #
# LiveTokenStream — rendering (captured console)
# --------------------------------------------------------------------------- #


def _captured_stream() -> tuple[LiveTokenStream, io.StringIO]:
    buf = io.StringIO()
    console_ = Console(file=buf, force_terminal=False, width=200)
    return LiveTokenStream(console_=console_), buf


def test_live_stream_prints_tokens_and_finishes() -> None:
    live, buf = _captured_stream()
    live.feed("Hello ")
    live.feed("world")
    live.finish()
    out = buf.getvalue()
    assert "Hello world" in out
    assert live.segment_printed is True


def test_live_stream_filters_think_tags() -> None:
    live, buf = _captured_stream()
    live.feed("<think>hidden</think>Hi there")
    live.finish()
    out = buf.getvalue()
    assert "hidden" not in out
    assert "Hi there" in out


def test_end_segment_closes_line_and_resets_state() -> None:
    live, buf = _captured_stream()
    live.feed("let me check…")
    live.end_segment()
    assert live.segment_printed is False
    assert "let me check…" in buf.getvalue()
    live.feed("continuing")
    live.finish()
    assert "continuing" in buf.getvalue()
    assert live.segment_printed is True


def test_finish_without_tokens_is_noop() -> None:
    live, buf = _captured_stream()
    live.finish()
    assert buf.getvalue() == ""
    assert live.segment_printed is False
