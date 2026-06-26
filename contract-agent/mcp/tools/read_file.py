"""
mcp/tools/read_file.py
----------------------
MCP Tool: read_file

Responsibility:
    Read a contract file from disk and return its plain-text content.
    Supports PDF (.pdf) and plain-text (.txt) formats.

Design principles (SOLID):
    - Single Responsibility: this module does exactly one thing — file reading.
    - Open/Closed: new formats can be added by extending _READERS without
      touching the public interface.
    - No side effects beyond filesystem reads — pure input/output, fully testable.
"""

import re
from pathlib import Path
from typing import Callable

from pypdf import PdfReader


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def read_file(file_path: str) -> dict[str, str]:
    """
    Read a contract file and return its plain-text content.

    Args:
        file_path: Absolute or relative path to the contract file.

    Returns:
        A dict with:
            "text"      — the full extracted text, whitespace-normalised
            "file_name" — the original filename (used by downstream tools)
            "format"    — "pdf" or "txt"

    Raises:
        FileNotFoundError: If the path does not exist on disk.
        ValueError:        If the file extension is not supported.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Contract file not found: {file_path}")

    suffix = path.suffix.lower()
    reader_fn = _READERS.get(suffix)

    if reader_fn is None:
        supported = ", ".join(_READERS.keys())
        raise ValueError(
            f"Unsupported format '{suffix}'. Supported formats: {supported}."
        )

    raw_text = reader_fn(path)

    return {
        "text": _normalize_whitespace(raw_text),
        "file_name": path.name,
        "format": suffix.lstrip("."),
    }


# ---------------------------------------------------------------------------
# Private format readers
# ---------------------------------------------------------------------------


def _read_pdf(path: Path) -> str:
    """Extract text from every page of a PDF and join with double newlines."""
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages)


def _read_txt(path: Path) -> str:
    """Read a plain-text file as UTF-8."""
    return path.read_text(encoding="utf-8")


# Registry mapping file extension → reader function.
# Add new formats here without changing read_file().
_READERS: dict[str, Callable[[Path], str]] = {
    ".pdf": _read_pdf,
    ".txt": _read_txt,
}


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _normalize_whitespace(text: str) -> str:
    """Collapse 3+ consecutive blank lines into a single paragraph break."""
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
