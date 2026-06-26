"""
crew/legal_analyst.py
---------------------
LegalAnalyst — CrewAI Agent

Responsibility:
    Define the LegalAnalyst agent and its dedicated tool (SearchClauseTool).
    This agent receives the ContractReader's structured extraction via task
    context and performs deep legal risk analysis — identifying clauses,
    obligations, red flags, and assigning risk ratings.

Design decisions:
    - SearchClauseTool wraps the MCP search_clause function. The analyst uses
      it to search for specific clause types (e.g. "indemnification", "liability")
      when it needs to verify exact wording before rating a risk.
    - The tool returns a human-readable summary of matches, not raw JSON,
      because the LLM processes the tool output directly in its reasoning.
    - allow_delegation=False: like the reader, this agent has a focused job.
      Delegation would introduce non-determinism into the analysis chain.
    - The agent does NOT receive the raw file path — it works from the
      ContractReader's output injected via task context. This enforces the
      separation of concerns: the reader reads, the analyst analyses.
"""

from __future__ import annotations

from typing import Type

from crewai import Agent
from crewai.tools import BaseTool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from agent_mcp.tools.search_clause import search_clause
from config.settings import load_prompt_section, settings

_PROMPT_FILE = settings.prompts_dir / "legal_analyst.md"


# ---------------------------------------------------------------------------
# Tool: SearchClauseTool
# ---------------------------------------------------------------------------


class _SearchClauseInput(BaseModel):
    """Input schema for SearchClauseTool."""
    text: str = Field(..., description="Full contract text to search within.")
    keyword: str = Field(..., description="Clause type or keyword to search for (case-insensitive).")
    context_lines: int = Field(default=3, description="Lines of context around each match.")


class SearchClauseTool(BaseTool):
    """
    CrewAI adapter wrapping the MCP search_clause function.

    Converts the list of ClauseMatch dataclasses into a readable text block
    that the LLM can parse and reason about. Each match is presented with
    its line number and surrounding context so the analyst can make an
    informed risk judgment from the exact clause wording.
    """

    name: str = "Search Contract Clause"
    description: str = (
        "Search for a specific keyword or clause type within the contract text. "
        "Returns every matching section with surrounding context. "
        "Use this to verify the exact wording of a clause before assigning a risk rating."
    )
    args_schema: Type[BaseModel] = _SearchClauseInput

    def _run(self, text: str, keyword: str, context_lines: int = 3) -> str:
        """Execute the MCP search and format results as readable text."""
        result = search_clause(text=text, keyword=keyword, context_lines=context_lines)

        if result["match_count"] == 0:
            return f"No matches found for keyword: '{keyword}'"

        lines = [f"Found {result['match_count']} match(es) for '{keyword}':\n"]

        for i, match in enumerate(result["matches"], start=1):
            m = match.to_dict()
            lines.append(f"--- Match {i} (line {m['line_number']}) ---")
            lines.append(m["context"])
            lines.append("")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------


def create_legal_analyst() -> Agent:
    """
    Instantiate and return a configured LegalAnalyst agent.

    The analyst is given the SearchClauseTool so it can drill into specific
    clause types identified during its reasoning. The ContractReader's full
    output is passed as task context (wired in analysis_task.py), not here.
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
        tools=[SearchClauseTool()],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )
