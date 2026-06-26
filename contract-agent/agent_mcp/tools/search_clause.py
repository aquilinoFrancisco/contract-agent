"""
mcp/tools/search_clause.py
--------------------------
MCP Tool: search_clause

Responsibility:
    Search for a specific keyword or clause type inside contract text and
    return every matching line with surrounding context.

Design principles (SOLID):
    - Single Responsibility: this module only performs text search — it has
      no knowledge of files, agents, or the MCP protocol.
    - Dependency Inversion: callers pass in plain strings; no hidden I/O.
    - Pure function — no side effects, deterministic, fully unit-testable.

Returns structured ClauseMatch dataclasses rather than raw strings so that
callers (the MCP server) can serialise results without parsing text.
"""

from dataclasses import asdict, dataclass


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ClauseMatch:
    """
    A single match found inside the contract text.

    Attributes:
        line_number:  1-based index of the line that matched the keyword.
        matched_line: The exact content of the matching line (stripped).
        context:      A window of lines surrounding the match, joined by newlines.
        keyword:      The search keyword that produced this match.
    """

    line_number: int
    matched_line: str
    context: str
    keyword: str

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable representation of this match."""
        return asdict(self)


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def search_clause(
    text: str,
    keyword: str,
    context_lines: int = 3,
) -> dict[str, object]:
    """
    Search for a keyword within contract text.

    Matching is case-insensitive. Each hit is returned with
    `context_lines` lines of surrounding text to preserve meaning.

    Args:
        text:          Full contract text to search within.
        keyword:       Word or phrase to look for (case-insensitive).
        context_lines: Lines of context to include above and below each match.
                       Must be >= 0. Defaults to 3.

    Returns:
        A dict with:
            "keyword"     — the original search term
            "match_count" — total number of lines that contained the keyword
            "matches"     — list of ClauseMatch instances (use .to_dict() for JSON)

    Raises:
        ValueError: If keyword is blank or context_lines is negative.
    """
    _validate_inputs(keyword, context_lines)

    lines = text.splitlines()
    keyword_lower = keyword.lower()
    matches: list[ClauseMatch] = []

    for i, line in enumerate(lines):
        if keyword_lower not in line.lower():
            continue

        context = _extract_context(lines, index=i, window=context_lines)

        matches.append(
            ClauseMatch(
                line_number=i + 1,          # Convert to 1-based for readability
                matched_line=line.strip(),
                context=context,
                keyword=keyword,
            )
        )

    return {
        "keyword": keyword,
        "match_count": len(matches),
        "matches": matches,                 # Server serialises these via .to_dict()
    }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _validate_inputs(keyword: str, context_lines: int) -> None:
    """Raise ValueError for invalid arguments before any processing begins."""
    if not keyword.strip():
        raise ValueError("'keyword' must be a non-empty string.")
    if context_lines < 0:
        raise ValueError("'context_lines' must be 0 or greater.")


def _extract_context(lines: list[str], index: int, window: int) -> str:
    """
    Slice a window of lines around a given index and join them.

    Clamps to the list boundaries so callers need not guard edge cases.
    """
    start = max(0, index - window)
    end = min(len(lines), index + window + 1)
    return "\n".join(lines[start:end])
