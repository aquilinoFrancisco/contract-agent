"""
config/logging.py
-----------------
Logging configuration for the Contract Agent.

Responsibility:
    Configure and return a consistently formatted logger for use across all
    modules. Centralising this here means log format, level, and handlers
    are controlled in one place and never scattered across individual files.

Usage (once implemented):
    from config.logging import get_logger
    logger = get_logger(__name__)
    logger.info("Graph node started.")
"""

from __future__ import annotations

import logging


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger.

    Configuration to be implemented:
        - Log level sourced from settings.log_level
        - Structured format: timestamp · level · module · message
        - Optional file handler for persistent logs
    """
    return logging.getLogger(name)
