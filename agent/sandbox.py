"""File sandbox tools — read / write / list / delete inside one root directory.

Safety model (stage 3, slimmed):
  - every path is resolved against ``SANDBOX_DIR`` and must stay inside it
    (``../`` escapes and absolute paths are rejected before any I/O);
  - dangerous operations (overwriting an existing file, deleting) require
    human confirmation:
      * an injectable hook (``set_confirm_hook``) — used by tests;
      * a y/N prompt in the interactive REPL;
      * auto-DENY when stdin is not a TTY (single-query / piped mode);
      * auto-ALLOW when ``SANDBOX_CONFIRM=false`` (scripting mode);
  - ``SANDBOX_ENABLED=false`` disables the tools entirely;
  - reads are truncated to ``SANDBOX_MAX_READ_CHARS`` to protect the context.
"""

import sys
from collections.abc import Callable
from pathlib import Path

from .config import config
from .tools import tool

_MAX_LIST_ENTRIES = 50

_CONFIRM_HOOK: Callable[[str], bool] | None = None


def set_confirm_hook(hook: Callable[[str], bool] | None) -> None:
    """Inject a confirmation callback (tests); ``None`` restores the default."""
    global _CONFIRM_HOOK
    _CONFIRM_HOOK = hook


def _confirm(prompt: str) -> bool:
    """Ask a human before a dangerous operation (see module docstring)."""
    if _CONFIRM_HOOK is not None:
        return _CONFIRM_HOOK(prompt)
    if not config.SANDBOX_CONFIRM:
        return True
    if not sys.stdin.isatty():
        return False
    try:
        return input(f"{prompt} [y/N] ").strip().lower() in ("y", "yes")
    except EOFError:
        return False


def _sandbox_root() -> Path:
    root = Path(config.SANDBOX_DIR).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _resolve_in_sandbox(path: str) -> Path:
    """Resolve ``path`` under the sandbox root, rejecting escapes."""
    root = _sandbox_root()
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        raise PermissionError(f"absolute paths are not allowed, use a relative path: {path!r}")
    resolved = (root / candidate).resolve()
    if resolved != root and not resolved.is_relative_to(root):
        raise PermissionError(f"path escapes the sandbox: {path!r}")
    return resolved


def _disabled() -> str:
    return "File tools are disabled (SANDBOX_ENABLED=false). Re-enable them to touch files."


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@tool
def read_file(path: str) -> str:
    """
    Read a UTF-8 text file stored inside the agent's file sandbox.

    Args:
        path: file path RELATIVE to the sandbox root, e.g. 'notes/todo.md'.
              Absolute paths and '../' escapes are rejected.

    Returns the file content (truncated for very large files), or a friendly
    error message. Only text files are supported.
    """
    if not config.SANDBOX_ENABLED:
        return _disabled()
    try:
        target = _resolve_in_sandbox(path)
    except (PermissionError, ValueError) as exc:
        return f"Rejected: {exc}"
    if not target.is_file():
        return f"File not found: {path}"
    text = target.read_text(encoding="utf-8", errors="replace")
    limit = config.SANDBOX_MAX_READ_CHARS
    if len(text) > limit:
        return text[:limit] + f"\n…[truncated — showing {limit} of {len(text)} chars]"
    return text


@tool
def write_file(path: str, content: str) -> str:
    """
    Write (create or overwrite) a UTF-8 text file inside the sandbox.

    Args:
        path: file path RELATIVE to the sandbox root; parent folders are
              created automatically. Absolute paths and '../' escapes are
              rejected.
        content: full text to write.

    Overwriting an existing file requires human confirmation. Binary files
    are not supported.
    """
    if not config.SANDBOX_ENABLED:
        return _disabled()
    try:
        target = _resolve_in_sandbox(path)
    except (PermissionError, ValueError) as exc:
        return f"Rejected: {exc}"
    if target.exists() and not _confirm(f"Overwrite existing file '{path}'?"):
        return f"Skipped: overwriting '{path}' was not confirmed."
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    except OSError as exc:
        return f"Could not write '{path}': {exc}"
    return f"Wrote {len(content)} chars to '{path}'."


@tool
def list_files(path: str = ".") -> str:
    """
    List files inside the agent's file sandbox (recursive).

    Args:
        path: subdirectory RELATIVE to the sandbox root; '.' (default) lists
              everything.

    Returns one relative path per line (capped at 50 entries), or a friendly
    error message.
    """
    if not config.SANDBOX_ENABLED:
        return _disabled()
    try:
        base = _resolve_in_sandbox(path)
    except (PermissionError, ValueError) as exc:
        return f"Rejected: {exc}"
    if not base.is_dir():
        return f"Not a directory: {path}"
    root = _sandbox_root()
    entries = sorted(p.relative_to(root).as_posix() for p in base.rglob("*") if p.is_file())
    if not entries:
        return f"No files under '{path}'."
    shown = entries[:_MAX_LIST_ENTRIES]
    more = f"\n… and {len(entries) - len(shown)} more" if len(entries) > len(shown) else ""
    return "\n".join(shown) + more


@tool
def delete_file(path: str) -> str:
    """
    Delete a file inside the agent's file sandbox (requires confirmation).

    Args:
        path: file path RELATIVE to the sandbox root. Absolute paths and
              '../' escapes are rejected. Directories cannot be deleted.

    A human must confirm before the file is removed.
    """
    if not config.SANDBOX_ENABLED:
        return _disabled()
    try:
        target = _resolve_in_sandbox(path)
    except (PermissionError, ValueError) as exc:
        return f"Rejected: {exc}"
    if not target.is_file():
        return f"File not found: {path}"
    if not _confirm(f"Delete '{path}'?"):
        return f"Skipped: deleting '{path}' was not confirmed."
    try:
        target.unlink()
    except OSError as exc:
        return f"Could not delete '{path}': {exc}"
    return f"Deleted '{path}'."
