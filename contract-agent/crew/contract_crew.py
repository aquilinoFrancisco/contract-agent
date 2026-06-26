"""
crew/contract_crew.py
---------------------
ContractCrew — Crew Assembly

Responsibility:
    Assemble all agents and tasks into a single executable CrewAI Crew and
    expose a clean run() interface to callers (the LangGraph workflow in Phase 4).

    This file is the only place where agents and tasks are wired together.
    All other crew/ files are independently importable — contract_crew.py is
    the integration point.

Design decisions:
    - ContractCrew is a class, not a function. A class gives the assembler a
      clear lifecycle (init → assemble → run) and makes it straightforward to
      inspect the crew's state (agents, tasks) in tests or debug sessions.
    - _assemble() is separated from __init__ to keep the constructor trivial
      and make the assembly logic easy to unit-test independently.
    - Process.sequential enforces a strict execution order:
        reading_task → analysis_task → summary_task
      Each task's output becomes the next task's context. A parallel or
      hierarchical process would break the information chain.
    - run() returns a plain string (the crew's final output). The LangGraph
      workflow in Phase 4 will receive this string and store it in the graph
      state. Returning a string (not a CrewOutput object) keeps this layer
      decoupled from LangGraph's state schema.
    - verbose=True on the Crew logs each agent's reasoning step to stdout.
      This is valuable in development and during demos. Set to False in
      production if log volume is a concern.

Usage:
    from crew.contract_crew import ContractCrew

    crew = ContractCrew(
        file_path="/path/to/contract.pdf",
        contract_name="service_agreement.pdf",
    )
    report: str = crew.run()
"""

from __future__ import annotations

from crewai import Crew, Process

from crew.contract_reader import create_contract_reader
from crew.executive_summarizer import create_executive_summarizer
from crew.legal_analyst import create_legal_analyst
from crew.analysis_task import create_analysis_task
from crew.reading_task import create_reading_task
from crew.summary_task import create_summary_task


class ContractCrew:
    """
    Orchestrates the full contract analysis pipeline.

    Assembles three agents and three chained tasks into a sequential CrewAI
    Crew, then exposes a single run() method that executes the pipeline and
    returns the final executive report as a string.

    Attributes:
        file_path:     Absolute path to the contract file to analyse.
        contract_name: Display name of the contract (used in the saved report).
    """

    def __init__(self, file_path: str, contract_name: str) -> None:
        """
        Args:
            file_path:     Path to the contract file on disk.
            contract_name: Human-readable name for the contract
                           (used in the report filename and header).
        """
        self.file_path = file_path
        self.contract_name = contract_name
        self._crew: Crew = self._assemble()

    def _assemble(self) -> Crew:
        """
        Build the full agent + task graph and return a configured Crew.

        Execution order (enforced by Process.sequential and task context):
            ContractReader  → reading_task   (reads file, extracts structure)
                ↓ context
            LegalAnalyst    → analysis_task  (analyses clauses, risks, obligations)
                ↓ context
            ExecutiveSummarizer → summary_task (writes + saves executive report)
        """
        # ------------------------------------------------------------------
        # Agents — each is independent; none knows about the others.
        # ------------------------------------------------------------------
        reader = create_contract_reader()
        analyst = create_legal_analyst()
        summarizer = create_executive_summarizer()

        # ------------------------------------------------------------------
        # Tasks — chained via context so each receives the previous output.
        # ------------------------------------------------------------------
        reading = create_reading_task(
            agent=reader,
            file_path=self.file_path,
        )
        analysis = create_analysis_task(
            agent=analyst,
            reading_task=reading,     # analyst receives reader's output
        )
        summary = create_summary_task(
            agent=summarizer,
            analysis_task=analysis,   # summariser receives analyst's output
            contract_name=self.contract_name,
        )

        # ------------------------------------------------------------------
        # Crew — sequential process guarantees reading → analysis → summary.
        # ------------------------------------------------------------------
        return Crew(
            agents=[reader, analyst, summarizer],
            tasks=[reading, analysis, summary],
            process=Process.sequential,
            verbose=True,
        )

    def run(self) -> str:
        """
        Execute the full contract analysis pipeline.

        Kicks off the crew and returns the ExecutiveSummarizer's final output
        as a plain string. The string contains the full executive report in
        the structured format defined by summary_task's expected_output.

        Returns:
            The complete executive report as a formatted string.

        Raises:
            Any exception from the underlying LLM calls or tool executions
            is allowed to propagate — the caller (LangGraph workflow) is
            responsible for error handling and state management.
        """
        result = self._crew.kickoff()
        # CrewAI returns a CrewOutput object; convert to str for clean interface.
        return str(result)
