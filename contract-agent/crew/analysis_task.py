"""
crew/analysis_task.py
---------------------
Analysis Task — CrewAI Task Definition

Responsibility:
    Define the factory function that creates the second task in the pipeline.
    The analysis task instructs the LegalAnalyst agent to perform deep legal
    risk analysis on the ContractReader's extraction output.

Design decisions:
    - context=[reading_task]: this is the key chain mechanism. CrewAI
      automatically injects the reading_task's output into the LegalAnalyst's
      prompt when this task runs. The analyst never needs to call read_file
      itself — it receives the already-extracted content as structured context.
    - The task description explicitly tells the agent to use its search tool
      for specific clause verification. Without this instruction, the agent
      might not use its tools even when they would improve accuracy.
    - expected_output is deliberately detailed. The ExecutiveSummarizer receives
      this output as its context — a vague or inconsistent analysis output would
      produce a vague summary. Garbage in, garbage out.
    - Risk levels (Low/Medium/High) are defined in the expected output template
      so the LLM uses a consistent vocabulary that matches the RiskLevel enum
      in models/schemas.py.
"""

from __future__ import annotations

from crewai import Agent, Task


def create_analysis_task(agent: Agent, reading_task: Task) -> Task:
    """
    Create the LegalAnalyst's risk analysis task.

    Args:
        agent:        The LegalAnalyst agent instance.
        reading_task: The completed reading task whose output is injected as context.

    Returns:
        A configured CrewAI Task ready to be added to a Crew.
    """
    return Task(
        description=(
            "You have been provided with a structured extraction of a legal contract "
            "(from the ContractReader agent). Perform a thorough legal risk analysis.\n\n"
            "For every major clause or section:\n"
            "1. Name the clause type (e.g. Payment, Termination, Indemnification, IP Ownership)\n"
            "2. Summarise its content in 1-2 sentences\n"
            "3. Assign a risk level: Low, Medium, or High\n"
            "4. Note any unusual, missing, or one-sided provisions\n\n"
            "Use the 'Search Contract Clause' tool whenever you need to verify the exact "
            "wording of a specific provision before assigning a risk rating.\n\n"
            "Also produce:\n"
            "- A list of all obligations for each named party\n"
            "- A list of red flags (unusual, absent, or dangerously one-sided clauses)\n"
            "- A list of standard clauses that are missing from this contract\n"
            "- An overall risk rating for the entire contract: Low, Medium, or High"
        ),
        expected_output=(
            "A structured legal risk analysis containing:\n\n"
            "CLAUSES:\n"
            "- [Clause Name] | Risk: [Low/Medium/High]\n"
            "  Summary: [1-2 sentence description]\n"
            "  Notes: [analyst commentary on risk or unusual aspects]\n"
            "(repeat for each identified clause)\n\n"
            "RED FLAGS:\n"
            "- [description of each red flag or unusual provision]\n\n"
            "MISSING STANDARD CLAUSES:\n"
            "- [list of standard clauses absent from this contract]\n\n"
            "OBLIGATIONS:\n"
            "- [Party Name]: [obligation description] | Deadline: [date or N/A]\n"
            "(repeat for each obligation)\n\n"
            "OVERALL RISK: [Low / Medium / High]\n"
            "Rationale: [2-3 sentence justification for the overall rating]"
        ),
        agent=agent,
        # context injects the reading_task's full output into this task's prompt.
        # This is how the analyst receives the extracted contract structure
        # without needing filesystem access of its own.
        context=[reading_task],
    )
