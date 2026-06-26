"""
graph/workflow.py
-----------------
LangGraph Workflow for the Contract Agent.

Responsibility:
    Assemble the five pipeline nodes and one conditional edge into a compiled
    StateGraph that orchestrates the full contract analysis pipeline.

Architecture rules (enforced in this file):
    1. Nodes are thin orchestrators — no business logic, no prompts, no regex
       beyond parsing the crew's structured output format.
    2. All agent processing is delegated to ContractCrew.run(). Nodes call it
       and store the result; they do not interpret legal text.
    3. No LLM calls in this file. LangGraph owns routing and state management;
       CrewAI owns language model interaction.
    4. No Streamlit imports or UI concerns. The compiled graph is a pure
       Python object that the UI layer invokes via graph.invoke(state).
    5. Errors are non-fatal at the node level. Any node that catches an
       exception appends to state["errors"] and returns without re-raising.
       The conditional edge after evaluate_risk routes to handle_error when
       errors are present.

Pipeline:

    START
      │
      ▼
    load_contract          Read the file; populate contract_text.
      │
      ▼
    run_contract_crew      Invoke ContractCrew; populate analysis.
      │
      ▼
    evaluate_risk          Parse risk_level, executive_summary, clauses.
      │
      ▼  route_after_evaluation()
      ├──── errors present ──────────────────────► handle_error ──► END
      │
      └──── Low / Medium / High ────────────────► save_report ───► END

Conditional edge decision:
    The routing function inspects state["errors"]. If any errors accumulated
    across the preceding nodes, the pipeline branches to handle_error.
    Otherwise it proceeds to save_report regardless of risk level, because
    even High-risk contracts should produce a saved report — the caller
    (Streamlit UI) decides what action to take based on risk_level.
    This keeps routing logic simple, deterministic, and testable.
"""

from __future__ import annotations

import re
from pathlib import Path

from langgraph.graph import END, START, StateGraph

from agent_mcp.tools.read_file import read_file
from crew import ContractCrew
from graph.state import ContractState

# ---------------------------------------------------------------------------
# Node: load_contract
# ---------------------------------------------------------------------------


def load_contract(state: ContractState) -> dict:
    """
    Read the contract file from disk and store its text in state.

    Uses the MCP read_file tool (same tool the ContractReader agent uses)
    so the text extraction logic is not duplicated between the graph and
    the crew. The node is stateless — it reads a path and returns text.

    Updates: contract_text, status
    On error: errors (appended), status = "error"
    """
    try:
        result = read_file(file_path=state["contract_path"])
        return {
            "contract_text": result["text"],
            "status": "contract_loaded",
        }
    except Exception as exc:
        return {
            "errors": [f"load_contract failed: {exc}"],
            "status": "error",
        }


# ---------------------------------------------------------------------------
# Node: run_contract_crew
# ---------------------------------------------------------------------------


def run_contract_crew(state: ContractState) -> dict:
    """
    Invoke the CrewAI pipeline and store the executive report in state.

    This node is the only place in the graph that knows about ContractCrew.
    It creates a crew instance, runs it, and stores the full string output.
    All agent logic (prompts, tool calls, LLM reasoning) happens inside the
    crew and is invisible to the graph layer.

    Guard: if a previous node has already recorded errors (e.g. file not
    found in load_contract), this node skips execution and lets the
    conditional edge route to handle_error.

    Updates: analysis, status
    On error: errors (appended), status = "error"
    """
    # Guard — skip if an upstream node already failed.
    if state["errors"]:
        return {"status": "error"}

    try:
        contract_name = Path(state["contract_path"]).name
        crew = ContractCrew(
            file_path=state["contract_path"],
            contract_name=contract_name,
        )
        analysis = crew.run()
        return {
            "analysis": analysis,
            "status": "crew_complete",
        }
    except Exception as exc:
        return {
            "errors": [f"run_contract_crew failed: {exc}"],
            "status": "error",
        }


# ---------------------------------------------------------------------------
# Node: evaluate_risk
# ---------------------------------------------------------------------------

# Patterns used to extract structured sections from the crew's report output.
# The crew (summary_task.py expected_output) produces these exact headers.
_RISK_PATTERN = re.compile(r"OVERALL RISK RATING[:\s]+(\w+)", re.IGNORECASE)
_SUMMARY_PATTERN = re.compile(
    r"EXECUTIVE SUMMARY\s*\n(.*?)(?=\n[A-Z ]{3,}\n|\Z)", re.DOTALL | re.IGNORECASE
)
_CLAUSE_PATTERN = re.compile(r"^\s*-\s+([^:|\n]+?)(?:\s*[:|])", re.MULTILINE)


def evaluate_risk(state: ContractState) -> dict:
    """
    Parse the crew output to extract risk level, summary, and clause names.

    This node does the minimum structural parsing needed to populate
    state fields that the graph's conditional edge and the Streamlit UI
    depend on. It does NOT perform legal analysis — that is the crew's job.

    Parsing strategy:
        - risk_level: regex search for "OVERALL RISK RATING: <word>"
        - executive_summary: regex capture between EXECUTIVE SUMMARY header
          and the next all-caps section header
        - extracted_clauses: regex capture of "- Clause Name:" bullet patterns
          from the KEY CLAUSES section

    Guard: skips if errors are already present.

    Updates: risk_level, executive_summary, extracted_clauses, status
    On error: errors (appended), risk_level = "", status = "error"
    """
    if state["errors"]:
        return {"status": "error"}

    analysis = state["analysis"]

    # Extract overall risk level
    risk_match = _RISK_PATTERN.search(analysis)
    if not risk_match:
        return {
            "errors": ["evaluate_risk: could not parse OVERALL RISK RATING from crew output."],
            "risk_level": "",
            "status": "error",
        }

    raw_risk = risk_match.group(1).strip().capitalize()
    if raw_risk not in ("Low", "Medium", "High"):
        return {
            "errors": [f"evaluate_risk: unexpected risk value '{raw_risk}' (expected Low/Medium/High)."],
            "risk_level": "",
            "status": "error",
        }

    # Extract executive summary (best-effort; falls back to empty string)
    summary_match = _SUMMARY_PATTERN.search(analysis)
    executive_summary = summary_match.group(1).strip() if summary_match else ""

    # Extract clause names from the KEY CLAUSES section (best-effort)
    extracted_clauses: list[str] = []
    key_clauses_pos = analysis.upper().find("KEY CLAUSES")
    if key_clauses_pos != -1:
        clauses_section = analysis[key_clauses_pos:]
        extracted_clauses = [
            m.group(1).strip()
            for m in _CLAUSE_PATTERN.finditer(clauses_section)
        ]

    return {
        "risk_level": raw_risk,
        "executive_summary": executive_summary,
        "extracted_clauses": extracted_clauses,
        "status": "evaluated",
    }


# ---------------------------------------------------------------------------
# Routing function (conditional edge)
# ---------------------------------------------------------------------------


def route_after_evaluation(state: ContractState) -> str:
    """
    Determine which node to execute after evaluate_risk.

    Returns:
        "save_report"  — if the pipeline is healthy (no errors, valid risk).
        "handle_error" — if any node has recorded an error.

    Design: all valid risk levels (Low, Medium, High) route to save_report
    because every analysed contract should produce a saved report. The caller
    (Streamlit UI) reads state["risk_level"] and decides how to present the
    result. The graph's job is routing, not policy.
    """
    if state["errors"]:
        return "handle_error"
    return "save_report"


# ---------------------------------------------------------------------------
# Node: save_report
# ---------------------------------------------------------------------------

_REPORT_PATH_PATTERN = re.compile(r"Path:\s*(.+\.md)", re.IGNORECASE)


def save_report(state: ContractState) -> dict:
    """
    Extract the saved report file path from the crew output and update state.

    The crew's SaveReportTool (executive_summarizer.py) already persisted the
    report to disk during run_contract_crew. This node simply parses the file
    path from the tool's confirmation string in the crew output and stores it
    in state so the Streamlit UI can display or link to the saved file.

    Updates: report_path, status
    """
    analysis = state["analysis"]
    path_match = _REPORT_PATH_PATTERN.search(analysis)
    report_path = path_match.group(1).strip() if path_match else ""

    return {
        "report_path": report_path,
        "status": "complete",
    }


# ---------------------------------------------------------------------------
# Node: handle_error
# ---------------------------------------------------------------------------


def handle_error(state: ContractState) -> dict:
    """
    Format accumulated errors and mark the pipeline as failed.

    Receives control when route_after_evaluation detects errors in state.
    Does not raise — the compiled graph returns the state dict to the caller,
    which is responsible for surfacing errors to the user.

    Updates: status
    """
    error_count = len(state["errors"])
    # Log to stdout (visible in Streamlit's terminal and LangGraph traces).
    print(f"[handle_error] Pipeline failed with {error_count} error(s):")
    for i, err in enumerate(state["errors"], start=1):
        print(f"  {i}. {err}")

    return {"status": "error"}


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def build_graph() -> object:
    """
    Assemble and compile the LangGraph StateGraph.

    Returns a compiled graph object with a .invoke(state) method.
    The graph is stateless — it can be compiled once at application startup
    and reused across multiple contract analyses.

    Graph structure:
        START → load_contract → run_contract_crew → evaluate_risk
             → [conditional] → save_report → END
                            → handle_error → END

    Returns:
        A compiled LangGraph graph (CompiledStateGraph).
    """
    workflow = StateGraph(ContractState)

    # --- Register nodes ---
    workflow.add_node("load_contract", load_contract)
    workflow.add_node("run_contract_crew", run_contract_crew)
    workflow.add_node("evaluate_risk", evaluate_risk)
    workflow.add_node("save_report", save_report)
    workflow.add_node("handle_error", handle_error)

    # --- Linear edges ---
    workflow.add_edge(START, "load_contract")
    workflow.add_edge("load_contract", "run_contract_crew")
    workflow.add_edge("run_contract_crew", "evaluate_risk")

    # --- Conditional edge: route based on error state and parsed risk level ---
    workflow.add_conditional_edges(
        "evaluate_risk",
        route_after_evaluation,
        {
            "save_report": "save_report",
            "handle_error": "handle_error",
        },
    )

    # --- Terminal edges ---
    workflow.add_edge("save_report", END)
    workflow.add_edge("handle_error", END)

    return workflow.compile()
