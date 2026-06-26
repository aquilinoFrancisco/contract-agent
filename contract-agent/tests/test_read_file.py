"""
tests/test_read_file.py
-----------------------
Validates mcp/tools/read_file.py:
  - reads a TXT file and returns the correct dict shape
  - normalises excessive whitespace
  - raises FileNotFoundError for missing paths
  - raises ValueError for unsupported extensions
"""

import sys
from pathlib import Path

# Make the contract-agent package importable when run from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from agent_mcp.tools.read_file import read_file, _normalize_whitespace


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def txt_contract(tmp_path: Path) -> Path:
    """Write a minimal contract text file and return its path."""
    content = "This Agreement is entered into by both parties.\n\nSection 1: Payment terms."
    contract = tmp_path / "sample_contract.txt"
    contract.write_text(content, encoding="utf-8")
    return contract


# ---------------------------------------------------------------------------
# Tests: read_file
# ---------------------------------------------------------------------------


def test_read_txt_returns_correct_keys(txt_contract: Path) -> None:
    """Result dict must contain exactly: text, file_name, format."""
    result = read_file(str(txt_contract))

    assert set(result.keys()) == {"text", "file_name", "format"}


def test_read_txt_returns_plain_dict(txt_contract: Path) -> None:
    """All values must be plain strings — no dataclasses or custom objects."""
    result = read_file(str(txt_contract))

    assert isinstance(result, dict)
    for value in result.values():
        assert isinstance(value, str)


def test_read_txt_content_is_correct(txt_contract: Path) -> None:
    """Extracted text must contain the original content."""
    result = read_file(str(txt_contract))

    assert "Agreement" in result["text"]
    assert "Payment terms" in result["text"]


def test_read_txt_format_field(txt_contract: Path) -> None:
    """Format field must be 'txt' for a .txt file."""
    result = read_file(str(txt_contract))

    assert result["format"] == "txt"


def test_read_txt_file_name_field(txt_contract: Path) -> None:
    """file_name field must match the original filename."""
    result = read_file(str(txt_contract))

    assert result["file_name"] == "sample_contract.txt"


def test_missing_file_raises_file_not_found() -> None:
    """A path that does not exist must raise FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="not found"):
        read_file("/nonexistent/path/contract.txt")


def test_unsupported_extension_raises_value_error(tmp_path: Path) -> None:
    """An unsupported extension must raise ValueError."""
    bad_file = tmp_path / "contract.docx"
    bad_file.write_text("content", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported format"):
        read_file(str(bad_file))


# ---------------------------------------------------------------------------
# Tests: _normalize_whitespace (private helper — tested directly)
# ---------------------------------------------------------------------------


def test_normalize_collapses_excessive_blank_lines() -> None:
    """Three or more consecutive newlines must be collapsed to two."""
    messy = "Clause 1.\n\n\n\n\nClause 2."
    result = _normalize_whitespace(messy)

    assert "\n\n\n" not in result
    assert "Clause 1." in result
    assert "Clause 2." in result


def test_normalize_strips_leading_trailing_whitespace() -> None:
    """Leading and trailing whitespace must be stripped."""
    result = _normalize_whitespace("   hello   ")

    assert result == "hello"
