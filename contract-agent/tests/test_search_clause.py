"""
tests/test_search_clause.py
---------------------------
Validates mcp/tools/search_clause.py:
  - returns a plain dict with correct keys
  - matches are case-insensitive
  - ClauseMatch instances are serialisable via .to_dict()
  - context window clamps correctly at text boundaries
  - raises ValueError on empty keyword or negative context_lines
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from agent_mcp.tools.search_clause import ClauseMatch, search_clause


CONTRACT_TEXT = """\
This Agreement ("Agreement") is entered into as of January 1, 2025.
The parties agree to the following terms and conditions.

Section 1: Payment
The Client shall pay the Contractor a fee of $10,000 per month.
Payment is due within 30 days of invoice.

Section 2: Termination
Either party may terminate this Agreement with 30 days written notice.
Termination does not release outstanding payment obligations.

Section 3: Confidentiality
All information shared under this Agreement is strictly confidential.
"""


# ---------------------------------------------------------------------------
# Tests: return shape
# ---------------------------------------------------------------------------


def test_returns_plain_dict() -> None:
    """Result must be a plain Python dict."""
    result = search_clause(CONTRACT_TEXT, "Payment")

    assert isinstance(result, dict)


def test_result_has_correct_keys() -> None:
    """Result dict must contain: keyword, match_count, matches."""
    result = search_clause(CONTRACT_TEXT, "Payment")

    assert set(result.keys()) == {"keyword", "match_count", "matches"}


def test_match_count_matches_list_length() -> None:
    """match_count must equal len(matches)."""
    result = search_clause(CONTRACT_TEXT, "payment")

    assert result["match_count"] == len(result["matches"])


# ---------------------------------------------------------------------------
# Tests: matching behaviour
# ---------------------------------------------------------------------------


def test_case_insensitive_match() -> None:
    """Search must be case-insensitive."""
    lower = search_clause(CONTRACT_TEXT, "payment")
    upper = search_clause(CONTRACT_TEXT, "PAYMENT")

    assert lower["match_count"] == upper["match_count"]


def test_finds_known_keyword() -> None:
    """'Termination' appears in the contract and must be found."""
    result = search_clause(CONTRACT_TEXT, "Termination")

    assert result["match_count"] > 0


def test_no_match_returns_empty_list() -> None:
    """A keyword not in the text must return zero matches."""
    result = search_clause(CONTRACT_TEXT, "arbitration")

    assert result["match_count"] == 0
    assert result["matches"] == []


def test_line_number_is_one_based() -> None:
    """line_number on a ClauseMatch must be 1-based (not 0-based)."""
    result = search_clause(CONTRACT_TEXT, "Agreement")
    first_match: ClauseMatch = result["matches"][0]

    assert first_match.line_number >= 1


# ---------------------------------------------------------------------------
# Tests: ClauseMatch serialisation
# ---------------------------------------------------------------------------


def test_clause_match_to_dict_is_plain_dict() -> None:
    """to_dict() must return a plain dict with string/int values only."""
    result = search_clause(CONTRACT_TEXT, "Payment")
    match: ClauseMatch = result["matches"][0]
    as_dict = match.to_dict()

    assert isinstance(as_dict, dict)
    assert isinstance(as_dict["line_number"], int)
    assert isinstance(as_dict["matched_line"], str)
    assert isinstance(as_dict["context"], str)
    assert isinstance(as_dict["keyword"], str)


def test_clause_match_to_dict_keys() -> None:
    """to_dict() must contain exactly the four expected keys."""
    result = search_clause(CONTRACT_TEXT, "Payment")
    as_dict = result["matches"][0].to_dict()

    assert set(as_dict.keys()) == {"line_number", "matched_line", "context", "keyword"}


# ---------------------------------------------------------------------------
# Tests: context window
# ---------------------------------------------------------------------------


def test_context_contains_surrounding_lines() -> None:
    """Context must include lines around the match, not just the match itself."""
    result = search_clause(CONTRACT_TEXT, "fee of", context_lines=2)
    match: ClauseMatch = result["matches"][0]

    # The line above "fee of" mentions "Section 1: Payment"
    assert len(match.context.splitlines()) > 1


def test_zero_context_lines() -> None:
    """context_lines=0 must return only the matching line itself."""
    result = search_clause(CONTRACT_TEXT, "fee of", context_lines=0)
    match: ClauseMatch = result["matches"][0]

    assert match.context.strip() == match.matched_line


# ---------------------------------------------------------------------------
# Tests: validation errors
# ---------------------------------------------------------------------------


def test_empty_keyword_raises_value_error() -> None:
    """An empty keyword string must raise ValueError."""
    with pytest.raises(ValueError, match="non-empty"):
        search_clause(CONTRACT_TEXT, "")


def test_blank_keyword_raises_value_error() -> None:
    """A whitespace-only keyword must raise ValueError."""
    with pytest.raises(ValueError, match="non-empty"):
        search_clause(CONTRACT_TEXT, "   ")


def test_negative_context_lines_raises_value_error() -> None:
    """Negative context_lines must raise ValueError."""
    with pytest.raises(ValueError, match="0 or greater"):
        search_clause(CONTRACT_TEXT, "Payment", context_lines=-1)
