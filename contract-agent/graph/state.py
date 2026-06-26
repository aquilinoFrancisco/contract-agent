"""
graph/state.py
--------------
LangGraph State Schema for the Contract Agent.

Responsibility:
    Define the single shared state object that flows through every node in the
    LangGraph workflow. Each node receives a full copy of ContractState and
    returns a partial dict containing only the fields it updates.

Design decisions:
    - TypedDict (not Pydantic BaseModel): LangGraph requires TypedDict for
      its StateGraph. Pydantic models are used for validated agent outputs
      (models/schemas.py); this TypedDict is LangGraph's runtime carrier.
    - Annotated[list[str], operator.add] on `errors`: LangGraph merges node
      return dicts with the existing state using each field's "reducer". The
      operator.add reducer means errors returned by any node are APPENDED to
      the existing list rather than replacing it. Every other field uses
      "last write wins" (the default), which is correct for scalar fields.
    - `extracted_clauses` is a list of clause name strings extracted by the
      evaluate_risk node. Keeping it as plain strings (not Clause objects)
      avoids pulling Pydantic models into the graph layer and keeps the state
      JSON-serialisable for LangGraph checkpointing.
    - `status` is a string lifecycle tag, not an Enum. The graph layer is
      kept lightweight; status strings are defined as string literals in
      workflow.py comments, not as a separate type.
    - initial_state() is a convenience factory for callers (Streamlit UI in
      Phase 5, tests). It ensures every field is always present in the state
      dict from the first node onwards — no node ever needs to guard against
      a missing key.
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict


class ContractState(TypedDict):
    """
    Shared mutable state passed between every node in the LangGraph workflow.

    Lifecycle of key fields:
        contract_path     → set by caller before graph invocation
        contract_text     → populated by load_contract node
        analysis          → populated by run_contract_crew node (full crew output)
        extracted_clauses → populated by evaluate_risk node
        risk_level        → populated by evaluate_risk node
        executive_summary → populated by evaluate_risk node
        report_path       → populated by save_report node
        errors            → appended by any node that catches an exception
        status            → updated by every node to reflect pipeline progress
    """

    # --- Input ---
    contract_path: str
    """Absolute path to the contract file. Set before graph.invoke() is called."""

    # --- Populated by load_contract ---
    contract_text: str
    """Full plain-text content of the contract file."""

    # --- Populated by run_contract_crew ---
    analysis: str
    """Raw string output from ContractCrew.run() — the complete executive report."""

    # --- Populated by evaluate_risk ---
    extracted_clauses: list[str]
    """Clause names extracted from the crew output. Used by the Streamlit UI."""

    risk_level: str
    """Overall risk rating: 'Low', 'Medium', 'High', or '' if unparseable."""

    executive_summary: str
    """The EXECUTIVE SUMMARY section extracted from the crew output."""

    # --- Populated by save_report ---
    report_path: str
    """Path to the saved .md report file. Populated once the report is persisted."""

    # --- Cross-cutting ---
    errors: Annotated[list[str], operator.add]
    """
    Accumulated error messages from any node.
    operator.add reducer ensures errors from multiple nodes are concatenated,
    not overwritten. Nodes append errors by returning {"errors": ["message"]}.
    """

    status: str
    """
    Lifecycle tag. Values used by the pipeline:
        "pending"          — initial state, not yet entered the graph
        "contract_loaded"  — load_contract succeeded
        "crew_running"     — run_contract_crew is executing
        "crew_complete"    — run_contract_crew succeeded
        "evaluated"        — evaluate_risk succeeded
        "complete"         — save_report succeeded; pipeline done
        "error"            — handle_error ran; see errors for details
    """


def initial_state(contract_path: str) -> ContractState:
    """
    Return a ContractState with all fields initialised to safe defaults.

    All downstream nodes depend on every field being present — TypedDict
    does not enforce field presence at runtime. Using this factory ensures
    a consistent, fully-populated state dict from the first node onwards.

    Args:
        contract_path: Absolute path to the contract file to be analysed.

    Returns:
        A ContractState with all fields populated and status set to "pending".
    """
    return ContractState(
        contract_path=contract_path,
        contract_text="",
        analysis="",
        extracted_clauses=[],
        risk_level="",
        executive_summary="",
        report_path="",
        errors=[],
        status="pending",
    )
