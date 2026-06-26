"""
tests/test_save_report.py
-------------------------
Validates mcp/tools/save_report.py:
  - writes a file to the given directory
  - returns a plain dict with file_path and file_name
  - filename is sanitised and timestamped
  - directory is created automatically if missing
  - raises ValueError for empty content
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from agent_mcp.tools.save_report import save_report, _build_filename


SAMPLE_REPORT = """\
CONTRACT ANALYSIS REPORT
========================

Executive Summary:
This is a standard service agreement between two parties.

Key Risks:
- Clause 7 lacks a liability cap.
"""


# ---------------------------------------------------------------------------
# Tests: return shape
# ---------------------------------------------------------------------------


def test_returns_plain_dict(tmp_path: Path) -> None:
    """Result must be a plain Python dict."""
    result = save_report("test_contract", SAMPLE_REPORT, reports_dir=tmp_path)

    assert isinstance(result, dict)


def test_result_has_correct_keys(tmp_path: Path) -> None:
    """Result dict must contain exactly: file_path, file_name."""
    result = save_report("test_contract", SAMPLE_REPORT, reports_dir=tmp_path)

    assert set(result.keys()) == {"file_path", "file_name"}


def test_all_values_are_strings(tmp_path: Path) -> None:
    """Both values in the result dict must be strings."""
    result = save_report("test_contract", SAMPLE_REPORT, reports_dir=tmp_path)

    assert isinstance(result["file_path"], str)
    assert isinstance(result["file_name"], str)


# ---------------------------------------------------------------------------
# Tests: file is actually written
# ---------------------------------------------------------------------------


def test_file_exists_after_save(tmp_path: Path) -> None:
    """The file referenced in file_path must exist on disk."""
    result = save_report("test_contract", SAMPLE_REPORT, reports_dir=tmp_path)

    assert Path(result["file_path"]).exists()


def test_file_content_matches_input(tmp_path: Path) -> None:
    """Written file content must match the report_content argument exactly."""
    result = save_report("test_contract", SAMPLE_REPORT, reports_dir=tmp_path)
    written = Path(result["file_path"]).read_text(encoding="utf-8")

    assert written == SAMPLE_REPORT


def test_creates_directory_if_missing(tmp_path: Path) -> None:
    """reports_dir must be created automatically when it does not exist."""
    nested = tmp_path / "deep" / "nested" / "reports"
    assert not nested.exists()

    save_report("test_contract", SAMPLE_REPORT, reports_dir=nested)

    assert nested.exists()


# ---------------------------------------------------------------------------
# Tests: filename format
# ---------------------------------------------------------------------------


def test_filename_ends_with_txt(tmp_path: Path) -> None:
    """Output filename must end with .txt."""
    result = save_report("my_contract", SAMPLE_REPORT, reports_dir=tmp_path)

    assert result["file_name"].endswith(".txt")


def test_filename_contains_sanitized_name(tmp_path: Path) -> None:
    """Sanitised contract name must appear in the filename."""
    result = save_report("my contract.pdf", SAMPLE_REPORT, reports_dir=tmp_path)

    # 'my contract.pdf' → stem 'my contract' → sanitised 'my_contract'
    assert "my_contract" in result["file_name"]


def test_filename_contains_timestamp(tmp_path: Path) -> None:
    """Filename must contain a timestamp segment (digits only, 8+ chars)."""
    result = save_report("contract", SAMPLE_REPORT, reports_dir=tmp_path)
    # Timestamp format: YYYYMMDD_HHMMSS — look for the date part (8 digits)
    import re
    assert re.search(r"\d{8}", result["file_name"])


def test_two_saves_produce_different_filenames(tmp_path: Path) -> None:
    """Two successive saves must not overwrite each other."""
    import time
    r1 = save_report("contract", SAMPLE_REPORT, reports_dir=tmp_path)
    time.sleep(1)  # Ensure timestamp differs by at least 1 second
    r2 = save_report("contract", SAMPLE_REPORT, reports_dir=tmp_path)

    assert r1["file_name"] != r2["file_name"]


# ---------------------------------------------------------------------------
# Tests: _build_filename helper
# ---------------------------------------------------------------------------


def test_build_filename_strips_extension() -> None:
    """A contract name with an extension must have the extension stripped."""
    name = _build_filename("contract.pdf")
    assert ".pdf" not in name


def test_build_filename_replaces_spaces() -> None:
    """Spaces must be replaced with underscores."""
    name = _build_filename("my service agreement")
    assert " " not in name


# ---------------------------------------------------------------------------
# Tests: validation errors
# ---------------------------------------------------------------------------


def test_empty_content_raises_value_error(tmp_path: Path) -> None:
    """Empty report_content must raise ValueError."""
    with pytest.raises(ValueError, match="must not be empty"):
        save_report("contract", "", reports_dir=tmp_path)


def test_whitespace_only_content_raises_value_error(tmp_path: Path) -> None:
    """Whitespace-only report_content must raise ValueError."""
    with pytest.raises(ValueError, match="must not be empty"):
        save_report("contract", "   \n  ", reports_dir=tmp_path)
