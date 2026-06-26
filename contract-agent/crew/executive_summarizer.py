"""
crew/executive_summarizer.py
----------------------------
ExecutiveSummarizer — CrewAI Agent

Responsibility:
    Define the ExecutiveSummarizer agent and its dedicated tool (SaveReportTool).
    This agent receives the LegalAnalyst's findings via task context and
    translates them into a plain-language executive report, then persists
    the report to disk using the MCP save_report function.

Design decisions:
    - SaveReportTool wraps the MCP save_report function. Persisting the report
      inside the agent (via a tool call) rather than externally keeps the
      pipeline self-contained: the tool call is part of the agent's reasoning
      chain, and the returned file path appears in the final crew output.
    - The agent's persona (prompt) is strongly opinionated about plain language
      and a single clear recommendation. This prevents the LLM from producing
      verbose, hedged executive summaries that fail to deliver actionable insight.
    - Temperature is inherited from settings (0.1 by default). Low temperature
      is appropriate even for the summariser — we want consistent, structured
      output, not creative variation.
    - allow_delegation=False: the summariser is the final node in the chain.
      Delegation at this stage would introduce latency with no benefit.
"""

from __future__ import annotations

from typing import Type

from crewai import Agent
from crewai.tools import BaseTool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from agent_mcp.tools.save_report import save_report
from config.settings import load_prompt_section, settings

_PROMPT_FILE = settings.prompts_dir / "executive_summarizer.md"


# ---------------------------------------------------------------------------
# Tool: SaveReportTool
# ---------------------------------------------------------------------------


class _SaveReportInput(BaseModel):
    """Input schema for SaveReportTool."""
    contract_name: str = Field(
        ...,
        description="Name of the source contract — used as the report filename base.",
    )
    report_content: str = Field(
        ...,
        description="The complete, finished executive report text to save to disk.",
    )


class SaveReportTool(BaseTool):
    """
    CrewAI adapter wrapping the MCP save_report function.

    The agent calls this tool as the last step of its task, passing the
    finished report content and the contract name. The tool persists the
    report to the reports/ directory and returns a confirmation string
    containing the saved file path.

    Returning the file path in the confirmation means the LLM includes it
    in the crew's final output — giving the Streamlit UI a concrete path
    to display or link to.
    """

    name: str = "Save Analysis Report"
    description: str = (
        "Save the finished contract analysis report to disk. "
        "Call this tool once the full executive report is written. "
        "Returns the path to the saved report file."
    )
    args_schema: Type[BaseModel] = _SaveReportInput

    def _run(self, contract_name: str, report_content: str) -> str:
        """Invoke the MCP save_report tool and return a human-readable confirmation."""
        result = save_report(
            contract_name=contract_name,
            report_content=report_content,
            reports_dir=settings.reports_dir,
        )
        return (
            f"Report saved successfully.\n"
            f"File: {result['file_name']}\n"
            f"Path: {result['file_path']}"
        )


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------


def create_executive_summarizer() -> Agent:
    """
    Instantiate and return a configured ExecutiveSummarizer agent.

    The SaveReportTool is provided so the agent can persist its output
    as part of its own reasoning step — not as an afterthought handled
    outside the crew.
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
        tools=[SaveReportTool()],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )
