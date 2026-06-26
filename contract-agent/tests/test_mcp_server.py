"""
tests/test_mcp_server.py
------------------------
Validates mcp/server.py dispatch behaviour without starting the stdio server.

Strategy:
  _dispatch() is a synchronous function extracted from the async handler
  specifically to make it unit-testable here. We test:
    - correct routing to each tool
    - structured error dicts on bad input
    - unknown tool names return a ValueError
    - TOOLS list exposes all three expected tool names
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json
import pytest

from agent_mcp.server import TOOLS, _dispatch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TOOL_NAMES = {tool.name for tool in TOOLS}

CONTRACT_TEXT = """\
This Agreement is between Alpha Corp and Beta Ltd.
Section 1: Payment of $5,000 due on the 1st of each month.
Section 2: Either party may terminate with 30 days notice.
"""


# ---------------------------------------------------------------------------
# Tests: TOOLS registry
# ---------------------------------------------------------------------------


def test_tools_list_exposes_three_tools() -> None:
    """Server must expose exactly three tools."""
    assert len(TOOLS) == 3


def test_tools_list_contains_read_file() -> None:
    assert "read_file" in TOOL_NAMES


def test_tools_list_contains_search_clause() -> None:
    assert "search_clause" in TOOL_NAMES


def test_tools_list_contains_save_report() -> None:
    assert "save_report" in TOOL_NAMES


def test_each_tool_has_required_mcp_fields() -> None:
    """Every Tool must have name, description, and inputSchema."""
    for tool in TOOLS:
        assert tool.name
        assert tool.description
        assert tool.inputSchema


# ---------------------------------------------------------------------------
# Tests: _dispatch — read_file routing
# ---------------------------------------------------------------------------


def test_dispatch_read_file_returns_dict(tmp_path: Path) -> None:
    """_dispatch('read_file', ...) must return a plain dict."""
    contract = tmp_path / "contract.txt"
    contract.write_text("Service agreement content.", encoding="utf-8")

    result = _dispatch("read_file", {"file_path": str(contract)})

    assert isinstance(result, dict)


def test_dispatch_read_file_result_is_json_serialisable(tmp_path: Path) -> None:
    """Result from read_file dispatch must be JSON-serialisable."""
    contract = tmp_path / "contract.txt"
    contract.write_text("Service agreement content.", encoding="utf-8")

    result = _dispatch("read_file", {"file_path": str(contract)})
    serialised = json.dumps(result)  # Must not raise

    assert isinstance(serialised, str)


def test_dispatch_read_file_missing_path_raises() -> None:
    """Missing file_path must propagate FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        _dispatch("read_file", {"file_path": "/nonexistent/contract.txt"})


# ---------------------------------------------------------------------------
# Tests: _dispatch — search_clause routing
# ---------------------------------------------------------------------------


def test_dispatch_search_clause_returns_dict() -> None:
    """_dispatch('search_clause', ...) must return a plain dict."""
    result = _dispatch("search_clause", {"text": CONTRACT_TEXT, "keyword": "Payment"})

    assert isinstance(result, dict)


def test_dispatch_search_clause_matches_are_plain_dicts() -> None:
    """
    Matches in the search_clause result must be plain dicts, not dataclasses.
    The server converts ClauseMatch instances via .to_dict() before returning.
    """
    result = _dispatch("search_clause", {"text": CONTRACT_TEXT, "keyword": "Payment"})

    for match in result["matches"]:
        assert isinstance(match, dict), "ClauseMatch was not converted to dict"


def test_dispatch_search_clause_result_is_json_serialisable() -> None:
    """Full search_clause result must be JSON-serialisable."""
    result = _dispatch("search_clause", {"text": CONTRACT_TEXT, "keyword": "terminate"})
    serialised = json.dumps(result)  # Must not raise

    assert isinstance(serialised, str)


def test_dispatch_search_clause_default_context_lines() -> None:
    """context_lines defaults to 3 when not provided."""
    result = _dispatch("search_clause", {"text": CONTRACT_TEXT, "keyword": "Payment"})
    # Should succeed without raising — default is applied inside _dispatch
    assert result["match_count"] >= 0


# ---------------------------------------------------------------------------
# Tests: _dispatch — save_report routing
# ---------------------------------------------------------------------------


def test_dispatch_save_report_returns_dict(tmp_path: Path, monkeypatch) -> None:
    """_dispatch('save_report', ...) must return a plain dict."""
    import agent_mcp.tools.save_report as sr_module
    monkeypatch.setattr(sr_module, "REPORTS_DIR", tmp_path)

    result = _dispatch(
        "save_report",
        {"contract_name": "test", "report_content": "Analysis complete."},
    )

    assert isinstance(result, dict)


def test_dispatch_save_report_result_is_json_serialisable(tmp_path: Path, monkeypatch) -> None:
    """Result from save_report dispatch must be JSON-serialisable."""
    import agent_mcp.tools.save_report as sr_module
    monkeypatch.setattr(sr_module, "REPORTS_DIR", tmp_path)

    result = _dispatch(
        "save_report",
        {"contract_name": "test", "report_content": "Analysis complete."},
    )
    serialised = json.dumps(result)  # Must not raise

    assert isinstance(serialised, str)


# ---------------------------------------------------------------------------
# Tests: _dispatch — unknown tool
# ---------------------------------------------------------------------------


def test_dispatch_unknown_tool_raises_value_error() -> None:
    """An unrecognised tool name must raise ValueError."""
    with pytest.raises(ValueError, match="Unknown tool"):
        _dispatch("nonexistent_tool", {})
