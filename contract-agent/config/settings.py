"""
config/settings.py
------------------
Central configuration for the Contract Agent.

Responsibility:
    Single source of truth for all runtime settings — API keys, model names,
    file paths, and feature flags. Every other module that needs a setting
    imports from here; nothing is hardcoded elsewhere.

    Settings are read from environment variables at import time, with
    sensible defaults for non-secret values. python-dotenv loads a local
    .env file in development; in production the host injects env vars directly.

Prompt loading:
    load_prompt_section() lives here (not in utils/) because prompt files are
    configuration — their location and parsing strategy are a single decision
    owned by this module.

Usage:
    from config.settings import settings, load_prompt_section
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from dotenv import load_dotenv

# Load .env file in development. In production this is a no-op because the
# real env vars are already set by the host — load_dotenv never overwrites
# existing environment variables.
load_dotenv()

# ---------------------------------------------------------------------------
# Project root — all other paths are derived from this.
# Layout: config/settings.py → parents[1] = contract-agent/
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


class Settings:
    """
    Application-wide settings, loaded from environment variables.

    Design decision — plain class rather than Pydantic BaseSettings:
        Pydantic BaseSettings is excellent but adds a dependency and hides the
        fact that `settings` is just a bag of typed values. A plain class with
        class-level defaults and os.environ lookups is transparent and avoids
        confusion between Pydantic model validation and configuration loading.
    """

    # ------------------------------------------------------------------
    # LLM
    # ------------------------------------------------------------------

    openai_api_key: str = os.environ.get("OPENAI_API_KEY", "")
    """Required. Set in .env or as an environment variable before running."""

    model_name: str = os.environ.get("MODEL_NAME", "gpt-4o")
    """OpenAI model used by all CrewAI agents."""

    temperature: float = float(os.environ.get("LLM_TEMPERATURE", "0.1"))
    """Low temperature = more deterministic, better for legal extraction."""

    # ------------------------------------------------------------------
    # Paths
    # ------------------------------------------------------------------

    project_root: Path = _PROJECT_ROOT
    contracts_dir: Path = _PROJECT_ROOT / "contracts"
    reports_dir: Path = _PROJECT_ROOT / "reports"
    prompts_dir: Path = _PROJECT_ROOT / "prompts"

    # ------------------------------------------------------------------
    # App
    # ------------------------------------------------------------------

    app_title: str = "Contract Agent"
    max_upload_size_mb: int = int(os.environ.get("MAX_UPLOAD_MB", "10"))

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    log_level: str = os.environ.get("LOG_LEVEL", "INFO")


# Module-level singleton.
# Import this object, not the class:  from config.settings import settings
settings = Settings()


# ---------------------------------------------------------------------------
# Prompt loader
# ---------------------------------------------------------------------------


def load_prompt_section(file_path: Path, section: str) -> str:
    """
    Extract a named section from a Markdown prompt file.

    Prompt files use ## headers to delimit sections, e.g.:

        ## Role
        Senior Contract Paralegal

        ## Goal
        Extract ...

    HTML comments (<!-- ... -->) are stripped before parsing so that prompt
    files can carry annotations and author notes that never reach the LLM.

    Args:
        file_path: Absolute path to the .md prompt file.
        section:   The exact section header text (without the ## prefix),
                   e.g. "Role", "Goal", "Backstory".

    Returns:
        The section content as a stripped plain-text string.

    Raises:
        FileNotFoundError: If the prompt file does not exist.
        ValueError:        If the section is not found in the file.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {file_path}")

    raw = file_path.read_text(encoding="utf-8")

    # Strip all HTML block comments so annotations stay out of prompts.
    clean = re.sub(r"<!--.*?-->", "", raw, flags=re.DOTALL)

    lines = clean.splitlines()
    capturing = False
    result_lines: list[str] = []

    for line in lines:
        # Detect the target section header (## Section Name)
        if re.match(rf"^##\s+{re.escape(section)}\s*$", line.strip()):
            capturing = True
            continue

        # Stop at the next ## header
        if capturing and line.strip().startswith("## "):
            break

        if capturing:
            result_lines.append(line)

    content = "\n".join(result_lines).strip()

    if not content:
        raise ValueError(
            f"Section '## {section}' not found or empty in: {file_path.name}"
        )

    return content
