"""
crew/summary_task.py
--------------------
Summary Task — CrewAI Task Definition

Responsibility:
    Define the factory function that creates the third and final task in the
    pipeline. The summary task instructs the ExecutiveSummarizer agent to
    translate the LegalAnalyst's findings into a plain-language executive
    report, then save it to disk.

Design decisions:
    - context=[analysis_task]: the summariser receives the analyst's structured
      output as context, not the raw contract text. This is intentional —
      the summariser should work from vetted legal findings, not re-derive
      conclusions from raw text.
    - contract_name is embedded in the description so the agent knows what
      name to pass to the SaveReportTool. The agent cannot infer this from
      the analysis output alone.
    - The expected_output defines the exact report structure. This template
      doubles as the schema that the Streamlit UI (Phase 4) will parse and
      render — consistent expected_output across runs is critical for reliable
      UI rendering.
    - The task explicitly instructs the agent to call SaveReportTool. Without
      this instruction, the agent might produce a complete report but forget
      to persist it — a common failure mode when an agent has optional tools.
"""

from __future__ import annotations

from crewai import Agent, Task


def create_summary_task(
    agent: Agent,
    analysis_task: Task,
    contract_name: str,
) -> Task:
    """
    Create the ExecutiveSummarizer's report generation task.

    Args:
        agent:         The ExecutiveSummarizer agent instance.
        analysis_task: The completed analysis task whose output is injected as context.
        contract_name: Name of the source contract — passed to the SaveReportTool.

    Returns:
        A configured CrewAI Task ready to be added to a Crew.
    """
    return Task(
        description=(
            "You have been provided with a complete legal risk analysis of a contract "
            "(from the LegalAnalyst agent). Write a plain-language executive report.\n\n"
            f"Contract name: {contract_name}\n\n"
            "Your report must include all of the following sections in order:\n\n"
            "1. EXECUTIVE SUMMARY\n"
            "   3-5 clear sentences explaining what this contract is, who the parties are, "
            "and its most important characteristics.\n\n"
            "2. KEY CLAUSES\n"
            "   Explain each important clause in plain English. No legal jargon. "
            "A business executive should understand each point immediately.\n\n"
            "3. RISKS & RED FLAGS\n"
            "   List risks in priority order (High risk first). Be direct — "
            "do not soften findings.\n\n"
            "4. OBLIGATIONS\n"
            "   For each party, list what they must do in plain English. "
            "Include deadlines where applicable.\n\n"
            "5. KEY DATES\n"
            "   List all important dates chronologically.\n\n"
            "6. OVERALL RISK RATING\n"
            "   State: Low, Medium, or High — with a one-sentence justification.\n\n"
            "7. RECOMMENDATION\n"
            "   One sentence. Actionable. Clear.\n\n"
            f"After writing the full report, use the 'Save Analysis Report' tool "
            f"with contract_name='{contract_name}' to save it to disk."
        ),
        expected_output=(
            "A complete executive report with these exact sections:\n\n"
            "CONTRACT ANALYSIS REPORT\n"
            "========================\n\n"
            "EXECUTIVE SUMMARY\n"
            "[3-5 plain-language sentences]\n\n"
            "KEY CLAUSES\n"
            "- [Clause]: [plain-language explanation]\n"
            "(repeat for each key clause)\n\n"
            "RISKS & RED FLAGS\n"
            "HIGH:\n"
            "- [risk description]\n"
            "MEDIUM:\n"
            "- [risk description]\n"
            "LOW:\n"
            "- [risk description]\n\n"
            "OBLIGATIONS\n"
            "[Party A]:\n"
            "- [obligation] (Deadline: [date or N/A])\n"
            "[Party B]:\n"
            "- [obligation] (Deadline: [date or N/A])\n\n"
            "KEY DATES\n"
            "- [date]: [what happens]\n\n"
            "OVERALL RISK RATING: [Low / Medium / High]\n"
            "Justification: [one sentence]\n\n"
            "RECOMMENDATION\n"
            "[One actionable sentence]\n\n"
            "---\n"
            "Report saved to: [file path returned by SaveReportTool]"
        ),
        agent=agent,
        # context injects the analysis_task's full output into this task's prompt.
        context=[analysis_task],
    )
