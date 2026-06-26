"""
utils/text_utils.py
-------------------
Shared text-processing utilities for the Contract Agent.

Responsibility:
    Pure-function, reusable helpers for working with strings and text.
    No file I/O, no LLM calls, no agent dependencies — just deterministic
    text transformations used across the MCP tools, agents, and graph nodes.

Functions to be implemented:
    - truncate(text, max_chars, suffix="...") -> str
        Truncate text to max_chars without cutting mid-word.

    - chunk_text(text, chunk_size, overlap) -> list[str]
        Split long contract text into overlapping chunks for LLM context limits.

    - clean_extracted_text(text) -> str
        Remove PDF artefacts (ligatures, stray hyphens, header/footer noise).

    - count_tokens(text, model) -> int
        Estimate the token count of a string for a given model using tiktoken.

    - extract_dates(text) -> list[str]
        Return all date-like strings found in the text (regex-based).

    - normalise_whitespace(text) -> str
        Collapse excessive blank lines and strip leading/trailing whitespace.
        (Mirrors the private helper in agent_mcp/tools/read_file.py but
        exposed here for use by other modules without importing from MCP layer.)
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Placeholder — implementations to be added in Phase 3
# ---------------------------------------------------------------------------


def truncate(text: str, max_chars: int, suffix: str = "...") -> str:
    """Truncate text to max_chars without cutting mid-word."""
    raise NotImplementedError


def chunk_text(text: str, chunk_size: int, overlap: int = 0) -> list[str]:
    """Split text into overlapping chunks for LLM context management."""
    raise NotImplementedError


def clean_extracted_text(text: str) -> str:
    """Remove common PDF extraction artefacts from contract text."""
    raise NotImplementedError


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """Estimate token count of text for the given model."""
    raise NotImplementedError


def extract_dates(text: str) -> list[str]:
    """Return all date-like strings found in the text."""
    raise NotImplementedError


def normalise_whitespace(text: str) -> str:
    """Collapse excessive blank lines and strip leading/trailing whitespace."""
    raise NotImplementedError
