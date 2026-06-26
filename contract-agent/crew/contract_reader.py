"""
crew/contract_reader.py
-----------------------
ContractReader — CrewAI Agent

Responsibility:
    Define the ContractReader agent and its dedicated tool (ReadFileTool).
    This agent's only job is to read a contract from disk and return a
    complete, structured extraction of its content — no analysis, no opinions.

Design decisions:
    - ReadFileTool is defined in this file (not in agent_mcp/) because it is
      a CrewAI-specific adapter. It wraps the MCP function and translates its
      dict return value into a plain string that the LLM can consume.
    - create_contract_reader() is a factory function, not a module-level
      instance. This prevents the LLM client from being initialised at import
      time — it is only created when a crew is being assembled.
    - allow_delegation=False: this agent never needs to hand off work.
      Disabling delegation avoids a CrewAI anti-pattern where an agent
      unexpectedly spawns sub-tasks, making the pipeline non-deterministic.
    - Prompts (role, goal, backstory) are loaded from prompts/contract_reader.md.
      Keeping prompts in Markdown means they can be edited without touching
      Python code and reviewed in git diffs like documentation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Type

from crewai import Agent
from crewai.tools import BaseTool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from agent_mcp.tools.read_file import read_file
from config.settings import load_prompt_section, settings

_PROMPT_FILE = settings.prompts_dir / "contract_reader.md"


# ---------------------------------------------------------------------------
# Tool: ReadFileTool
# ---------------------------------------------------------------------------


class _ReadFileInput(BaseModel):
    """Input schema for ReadFileTool."""
    file_path: str = Field(
        ...,
        description="Absolute or relative path to the contract file (PDF or TXT).",
    )


class ReadFileTool(BaseTool):
    """
    CrewAI adapter wrapping the MCP read_file function.

    Why a thin adapter and not a direct import?
        CrewAI tools must return strings so the LLM can process the result.
        The underlying MCP function returns a dict. This adapter translates
        between the two interfaces without modifying either side — a textbook
        application of the Adapter pattern.
    """

    name: str = "Read Contract File"
    description: str = (
        "Read a contract file (PDF or TXT) from disk and return its full plain-text content. "
        "Always use this tool first before attempting any analysis."
    )
    args_schema: Type[BaseModel] = _ReadFileInput

    def _run(self, file_path: str) -> str:
        """Invoke the MCP tool and return just the extracted text."""
        result = read_file(file_path=file_path)
        # Return format: brief header + full text.
        # The header gives the LLM context about what it received.
        return (
            f"[File: {result['file_name']} | Format: {result['format']}]\n\n"
            f"{result['text']}"
        )


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------


def create_contract_reader() -> Agent:
    """
    Instantiate and return a configured ContractReader agent.

    The LLM is constructed here (not at module level) so that the
    OPENAI_API_KEY is only required when actually running the pipeline,
    not at import time. This keeps test environments clean.
    """
    llm = ChatOpenAI(
        model=settings.model_name,
        temperature=settings.temperature,
        api_key=settings.openai_api_key or None,
    )

    return Agent(
        role=load_prompt_section(_PROMPT_FILE, "Role"),
        goal=load_prompt_section(_PROMPT_FILE, "Goal"),
        backstory=load_prompt_section(_PROMPT_FILE, "Backstory"),
        tools=[ReadFileTool()],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )
