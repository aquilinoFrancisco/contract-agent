"""
crew/reading_task.py
--------------------
Reading Task — CrewAI Task Definition

Responsibility:
    Define the factory function that creates the first task in the pipeline.
    The reading task instructs the ContractReader agent to use its ReadFileTool
    to read the contract and return a complete structured extraction.

Design decisions:
    - Factory function pattern (create_reading_task) rather than a module-level
      Task instance: the file_path is only known at runtime (when the user
      uploads a file), so the task cannot be created at import time.
    - The file_path is embedded in the task description. CrewAI injects
      task descriptions into the agent's prompt, so the agent receives the
      exact path it must pass to its tool.
    - expected_output is explicit and structured. A well-defined expected_output
      guides the LLM toward a consistent format, which is critical because the
      LegalAnalyst receives this output as context — ambiguous output cascades
      into poor analysis.
    - This task has no `context` parameter — it is the first node and has no
      upstream dependency.
"""

from __future__ import annotations

from crewai import Agent, Task


def create_reading_task(agent: Agent, file_path: str) -> Task:
    """
    Create the ContractReader's extraction task.

    Args:
        agent:     The ContractReader agent instance.
        file_path: Absolute path to the contract file to read.

    Returns:
        A configured CrewAI Task ready to be added to a Crew.
    """
    return Task(
        description=(
            f"Read the legal contract located at: {file_path}\n\n"
            "Use the 'Read Contract File' tool to load the full document text.\n\n"
            "Then extract and report ALL of the following:\n"
            "1. Contract type (e.g. NDA, Service Agreement, Employment Contract, Licensing Agreement)\n"
            "2. All named parties — full legal names as they appear in the document\n"
            "3. Effective date and expiry/termination date (if stated)\n"
            "4. All other dates mentioned: deadlines, notice periods, renewal windows\n"
            "5. All section and article headings, in order\n"
            "6. Governing law / jurisdiction clause (if present)\n\n"
            "Do not interpret or analyse. Extract only. Be complete and precise."
        ),
        expected_output=(
            "A structured extraction report containing:\n"
            "- Contract Type: [type]\n"
            "- Parties: [list of all named parties]\n"
            "- Effective Date: [date or 'Not stated']\n"
            "- Expiry Date: [date or 'Not stated']\n"
            "- Key Dates: [bulleted list of all dates with context]\n"
            "- Section Headings: [numbered list of all sections]\n"
            "- Governing Law: [jurisdiction or 'Not stated']"
        ),
        agent=agent,
        # No context — this is the first task in the chain.
    )
