"""File sandbox tools: containment, confirmation, disabled mode."""

from pathlib import Path

import pytest

from agent import sandbox
from agent.config import config


@pytest.fixture()
def box(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the sandbox at a temp dir with confirmations enabled."""
    monkeypatch.setattr(config, "SANDBOX_DIR", str(tmp_path / "box"))
    monkeypatch.setattr(config, "SANDBOX_ENABLED", True)
    monkeypatch.setattr(config, "SANDBOX_CONFIRM", True)
    monkeypatch.setattr(config, "SANDBOX_MAX_READ_CHARS", 8000)
    sandbox.set_confirm_hook(None)
    yield sandbox._sandbox_root()
    sandbox.set_confirm_hook(None)


def test_write_read_roundtrip(box: Path) -> None:
    out = sandbox.write_file.invoke({"path": "notes/a.txt", "content": "hello sandbox"})
    assert "Wrote 13 chars" in out
    assert (box / "notes" / "a.txt").read_text() == "hello sandbox"
    assert sandbox.read_file.invoke({"path": "notes/a.txt"}) == "hello sandbox"


def test_rejects_parent_escape(box: Path) -> None:
    out = sandbox.write_file.invoke({"path": "../evil.txt", "content": "x"})
    assert "Rejected" in out and "escapes the sandbox" in out
    assert not (box.parent / "evil.txt").exists()
    assert "Rejected" in sandbox.read_file.invoke({"path": "../../etc/passwd"})


def test_rejects_absolute_paths(box: Path) -> None:
    out = sandbox.read_file.invoke({"path": "/etc/passwd"})
    assert "Rejected" in out and "absolute" in out


def test_list_files_relative_paths(box: Path) -> None:
    sandbox.write_file.invoke({"path": "a/b.txt", "content": "1"})
    sandbox.write_file.invoke({"path": "c.txt", "content": "2"})
    listing = sandbox.list_files.invoke({"path": "."})
    assert "a/b.txt" in listing
    assert "c.txt" in listing


def test_delete_needs_confirm(box: Path) -> None:
    sandbox.write_file.invoke({"path": "d.txt", "content": "data"})
    sandbox.set_confirm_hook(lambda prompt: False)
    out = sandbox.delete_file.invoke({"path": "d.txt"})
    assert "Skipped" in out and "not confirmed" in out
    assert (box / "d.txt").exists()
    sandbox.set_confirm_hook(lambda prompt: True)
    assert "Deleted" in sandbox.delete_file.invoke({"path": "d.txt"})
    assert not (box / "d.txt").exists()


def test_overwrite_needs_confirm(box: Path) -> None:
    sandbox.write_file.invoke({"path": "keep.txt", "content": "original"})
    sandbox.set_confirm_hook(lambda prompt: False)
    out = sandbox.write_file.invoke({"path": "keep.txt", "content": "clobbered"})
    assert "Skipped" in out
    assert (box / "keep.txt").read_text() == "original"


def test_non_tty_auto_denies_dangerous_ops(box: Path) -> None:
    # Under pytest stdin is not a TTY and no hook is set → dangerous ops denied.
    sandbox.write_file.invoke({"path": "t.txt", "content": "v1"})
    assert "Skipped" in sandbox.delete_file.invoke({"path": "t.txt"})
    assert "Skipped" in sandbox.write_file.invoke({"path": "t.txt", "content": "v2"})


def test_scripting_mode_allows(box: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "SANDBOX_CONFIRM", False)
    sandbox.write_file.invoke({"path": "s.txt", "content": "bye"})
    assert "Deleted" in sandbox.delete_file.invoke({"path": "s.txt"})


def test_disabled_mode(box: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "SANDBOX_ENABLED", False)
    assert "disabled" in sandbox.read_file.invoke({"path": "x"})
    assert "disabled" in sandbox.write_file.invoke({"path": "x", "content": "y"})
    assert "disabled" in sandbox.list_files.invoke({})
    assert "disabled" in sandbox.delete_file.invoke({"path": "x"})


def test_read_truncation(box: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "SANDBOX_MAX_READ_CHARS", 200)
    sandbox.write_file.invoke({"path": "big.txt", "content": "x" * 1000})
    out = sandbox.read_file.invoke({"path": "big.txt"})
    assert "truncated" in out
    assert "1000" in out
