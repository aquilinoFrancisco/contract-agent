"""
utils/file_utils.py
-------------------
Shared file-handling utilities for the Contract Agent.

Responsibility:
    Low-level, reusable helpers for working with files and directories.
    These utilities have no knowledge of contracts, agents, or the MCP
    protocol — they solve generic filesystem problems that multiple modules
    need.

    Business-logic-free: these functions take paths and return data.
    They do not call any LLM, agent, or external service.

Functions to be implemented (used by MCP tools, Streamlit, and graph nodes):
    - save_upload(uploaded_file, destination_dir) -> Path
        Save a Streamlit UploadedFile object to a directory and return its path.

    - get_file_extension(path) -> str
        Return the lowercase extension of a file, e.g. ".pdf".

    - ensure_dir(path) -> Path
        Create a directory (and parents) if it does not exist. Idempotent.

    - list_files(directory, extension) -> list[Path]
        Return all files in a directory matching a given extension.

    - file_size_mb(path) -> float
        Return the size of a file in megabytes.
"""

from __future__ import annotations

from pathlib import Path


# ---------------------------------------------------------------------------
# Placeholder — implementations to be added in Phase 3
# ---------------------------------------------------------------------------


def save_upload(uploaded_file: object, destination_dir: Path) -> Path:
    """Save an uploaded file to disk and return its path."""
    raise NotImplementedError


def get_file_extension(path: Path | str) -> str:
    """Return the lowercase extension of a file."""
    raise NotImplementedError


def ensure_dir(path: Path | str) -> Path:
    """Create a directory and all parents if they do not exist."""
    raise NotImplementedError


def list_files(directory: Path | str, extension: str) -> list[Path]:
    """Return all files in a directory matching a given extension."""
    raise NotImplementedError


def file_size_mb(path: Path | str) -> float:
    """Return the size of a file in megabytes."""
    raise NotImplementedError
