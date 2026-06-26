"""
mcp/tools/save_report.py
------------------------
MCP Tool: save_report

Responsibility:
    Persist a finished contract analysis report to the reports/ directory.
    Each report receives a UTC timestamp in its filename to prevent overwrites
    and to maintain a natural audit trail.

Design principles (SOLID):
    - Single Responsibility: this module only writes reports — it does not
      format, summarise, or parse anything.
    - Dependency Inversion: the reports directory is injected via a parameter
      (defaults to the project-level reports/ folder) so tests can redirect
      output without touching the real filesystem.
    - Idempotent setup: the output directory is created automatically if it
      does not exist — safe to call in any environment.
"""

import re
from datetime import datetime, timezone
from pathlib import Path


# Default output directory, resolved relative to this file's location.
# Layout: contract-agent/mcp/tools/save_report.py → parents[2] = contract-agent/
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR: Path = _PROJECT_ROOT / "reports"


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def save_report(
    contract_name: str,
    report_content: str,
    reports_dir: Path = REPORTS_DIR,
) -> dict[str, str]:
    """
    Save a contract analysis report to disk.

    Output filename format:
        <sanitized_contract_name>_<YYYYMMDD_HHMMSS_UTC>.txt

    Args:
        contract_name:  Name of the source contract. Used in the filename;
                        any characters that are invalid in filenames are
                        replaced with underscores.
        report_content: Full text content of the finished analysis report.
        reports_dir:    Destination directory. Defaults to the project-level
                        reports/ folder. Pass a tmp path in tests.

    Returns:
        A dict with:
            "file_path" — absolute path to the written file
            "file_name" — just the filename (useful for UI display)

    Raises:
        ValueError: If report_content is empty.
        OSError:    If the file cannot be written (permissions, disk full, etc.)
    """
    if not report_content.strip():
        raise ValueError("'report_content' must not be empty.")

    reports_dir.mkdir(parents=True, exist_ok=True)

    file_name = _build_filename(contract_name)
    file_path = reports_dir / file_name

    file_path.write_text(report_content, encoding="utf-8")

    return {
        "file_path": str(file_path.resolve()),
        "file_name": file_name,
    }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _build_filename(contract_name: str) -> str:
    """
    Construct a unique, filesystem-safe filename for the report.

    Steps:
        1. Strip any file extension the caller may have included.
        2. Replace non-alphanumeric characters with underscores.
        3. Append a UTC timestamp for uniqueness.
    """
    stem = Path(contract_name).stem                   # Drop extension if present
    sanitized = re.sub(r"[^\w\-]", "_", stem)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{sanitized}_{timestamp}.txt"
