"""
config/settings.py
------------------
Central configuration for the Contract Agent.

Responsibility:
    Single source of truth for all runtime settings — API keys, model names,
    file paths, timeouts, and feature flags. Every other module imports from
    here; no module hardcodes a value that could ever change.

    Settings are loaded from environment variables (via python-dotenv) so the
    application works identically in local dev, CI, and production without
    code changes.

Usage (once implemented):
    from config.settings import settings
    client = OpenAI(api_key=settings.openai_api_key)
"""

from __future__ import annotations


class Settings:
    """
    Application-wide settings.

    Sections (to be implemented):
        - LLM        : model name, temperature, max_tokens, API key
        - Paths      : contracts_dir, reports_dir, prompts_dir
        - MCP        : server name, tool timeout
        - Logging    : log level, log format
        - App        : app title, max upload size in MB
    """

    pass


# Module-level singleton — import this, not the class.
settings = Settings()
