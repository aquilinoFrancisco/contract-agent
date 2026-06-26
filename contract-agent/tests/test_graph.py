"""
tests/test_graph.py
-------------------
Tests for the LangGraph state schema and workflow.

Test strategy:
    - Node functions are tested in isolation using mocked dependencies.
      No LLM calls, no disk writes beyond what the MCP tools already test.
    - The routing function is tested directly with hand-crafted states —
      it is pure Python with no side effects.
    - build_graph() is tested to confirm it compiles without error and
      exposes the expected nodes.
    - The graph is NOT invoked end-to-end here (that would require a live
      OpenAI key). End-to-end tests belong in a separate integration suite.

Coverage:
    - ContractState: field presence, initial_state factory
    - route_after_evaluation: all routing branches
    - load_contract: success path, file-not-found error path
    - run_contract_crew: success path, guard (errors present), exception path
    - evaluate_risk: success path, missing risk pattern, bad risk value, guard
    - save_report: path extraction, missing path fallback
    - handle_error: status update
    - build_graph: compiles, expected nodes present
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from graph.state import ContractState, initial_state
from graph.workflow import (
    build_graph,
    evaluate_risk,
    handle_error,
    load_contract,
    route_after_evaluation,
    run_contract_crew,
    save_report,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_CREW_OUTPUT = """\
CONTRACT ANALYSIS REPORT
========================

EXECUTIVE SUMMARY
This is a standard service agreement between Alpha Corp and Beta Ltd.
It runs for one year and includes standard payment terms.

KEY CLAUSES
- Payment Terms: Due within 30 days of invoice.
- Termination: Either party may terminate with 30 days notice.
- Confidentiality: Standard mutual NDA provisions apply.

RISKS & RED FLAGS
HIGH:
- No liability cap specified.
MEDIUM:
- Auto-renewal clause buried in Section 12.
LOW:
- Minor ambiguity in the "Force Majeure" definition.

OBLIGATIONS
Alpha Corp:
- Pay monthly fee of $5,000 (Deadline: 1st of each month)
Beta Ltd:
- Deliver services as described in Schedule A (Deadline: N/A)

KEY DATES
- 2025-01-01: Contract effective date
- 2025-12-31: Contract expiry date

OVERALL RISK RATING: High
Justification: Absence of a liability cap exposes both parties to unlimited liability.

RECOMMENDATION
Do not sign without negotiating a mutual liability cap.

---
Report saved to: /home/user/contracts/reports/service_agreement_20250101_120000.md
Path: /home/user/contracts/reports/service_agreement_20250101_120000.md
"""


def make_state(**overrides) -> ContractState:
    """Return a ContractState with defaults, with optional field overrides."""
    base = initial_state("/tmp/test_contract.pdf")
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# ContractState
# ---------------------------------------------------------------------------


class TestContractState:
    """Verify the TypedDict schema and initial_state factory."""

    REQUIRED_FIELDS = {
        "contract_path",
        "contract_text",
        "analysis",
        "extracted_clauses",
        "risk_level",
        "executive_summary",
        "report_path",
        "errors",
        "status",
    }

    def test_initial_state_contains_all_required_fields(self):
        state = initial_state("/tmp/contract.pdf")
        assert self.REQUIRED_FIELDS.issubset(set(state.keys()))

    def test_initial_state_contract_path_is_set(self):
        state = initial_state("/tmp/contract.pdf")
        assert state["contract_path"] == "/tmp/contract.pdf"

    def test_initial_state_errors_is_empty_list(self):
        state = initial_state("/tmp/contract.pdf")
        assert state["errors"] == []

    def test_initial_state_status_is_pending(self):
        state = initial_state("/tmp/contract.pdf")
        assert state["status"] == "pending"

    def test_initial_state_list_fields_are_empty(self):
        state = initial_state("/tmp/contract.pdf")
        assert state["extracted_clauses"] == []

    def test_initial_state_string_fields_are_empty(self):
        state = initial_state("/tmp/contract.pdf")
        for field in ("contract_text", "analysis", "risk_level", "executive_summary", "report_path"):
            assert state[field] == "", f"Expected '{field}' to be empty string"


# ---------------------------------------------------------------------------
# route_after_evaluation
# ---------------------------------------------------------------------------


class TestRouteAfterEvaluation:
    """Verify the conditional edge routing function covers all branches."""

    def test_routes_to_save_report_when_risk_is_low(self):
        state = make_state(risk_level="Low", errors=[])
        assert route_after_evaluation(state) == "save_report"

    def test_routes_to_save_report_when_risk_is_medium(self):
        state = make_state(risk_level="Medium", errors=[])
        assert route_after_evaluation(state) == "save_report"

    def test_routes_to_save_report_when_risk_is_high(self):
        state = make_state(risk_level="High", errors=[])
        assert route_after_evaluation(state) == "save_report"

    def test_routes_to_handle_error_when_errors_present(self):
        state = make_state(risk_level="", errors=["Something broke"])
        assert route_after_evaluation(state) == "handle_error"

    def test_routes_to_handle_error_with_multiple_errors(self):
        state = make_state(errors=["Error A", "Error B"])
        assert route_after_evaluation(state) == "handle_error"

    def test_routes_to_handle_error_when_errors_nonempty_despite_valid_risk(self):
        # Errors take priority over a valid risk level.
        state = make_state(risk_level="High", errors=["Partial failure"])
        assert route_after_evaluation(state) == "handle_error"


# ---------------------------------------------------------------------------
# Node: load_contract
# ---------------------------------------------------------------------------


class TestLoadContractNode:
    """Verify file loading and error handling."""

    def test_success_populates_contract_text(self):
        with patch("graph.workflow.read_file") as mock_read:
            mock_read.return_value = {
                "text": "This is the contract text.",
                "file_name": "test.pdf",
                "format": "pdf",
            }
            result = load_contract(make_state())

        assert result["contract_text"] == "This is the contract text."
        assert result["status"] == "contract_loaded"
        assert "errors" not in result  # node must not return empty errors list

    def test_file_not_found_populates_errors(self):
        with patch("graph.workflow.read_file") as mock_read:
            mock_read.side_effect = FileNotFoundError("No such file: /tmp/test.pdf")
            result = load_contract(make_state())

        assert result["errors"] == ["load_contract failed: No such file: /tmp/test.pdf"]
        assert result["status"] == "error"

    def test_arbitrary_exception_is_caught(self):
        with patch("graph.workflow.read_file") as mock_read:
            mock_read.side_effect = RuntimeError("Unexpected failure")
            result = load_contract(make_state())

        assert len(result["errors"]) == 1
        assert "run_contract_crew" not in result["errors"][0]  # correct node name
        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# Node: run_contract_crew
# ---------------------------------------------------------------------------


class TestRunContractCrewNode:
    """Verify crew invocation, guard behaviour, and exception handling."""

    def test_success_populates_analysis(self):
        with patch("graph.workflow.ContractCrew") as MockCrew:
            MockCrew.return_value.run.return_value = SAMPLE_CREW_OUTPUT
            result = run_contract_crew(
                make_state(contract_path="/tmp/contract.pdf", contract_text="text")
            )

        assert result["analysis"] == SAMPLE_CREW_OUTPUT
        assert result["status"] == "crew_complete"

    def test_guard_skips_when_errors_already_present(self):
        with patch("graph.workflow.ContractCrew") as MockCrew:
            result = run_contract_crew(
                make_state(errors=["load_contract failed: file missing"])
            )
            # Crew must NOT be instantiated when errors are present
            MockCrew.assert_not_called()

        assert result["status"] == "error"

    def test_crew_exception_is_caught_and_added_to_errors(self):
        with patch("graph.workflow.ContractCrew") as MockCrew:
            MockCrew.return_value.run.side_effect = RuntimeError("LLM timeout")
            result = run_contract_crew(
                make_state(contract_path="/tmp/contract.pdf", contract_text="text")
            )

        assert any("run_contract_crew failed" in e for e in result["errors"])
        assert result["status"] == "error"

    def test_contract_name_is_derived_from_path(self):
        """Crew must be instantiated with contract_name = basename of the path."""
        with patch("graph.workflow.ContractCrew") as MockCrew:
            MockCrew.return_value.run.return_value = "report"
            run_contract_crew(make_state(contract_path="/docs/my_contract.pdf"))
            MockCrew.assert_called_once_with(
                file_path="/docs/my_contract.pdf",
                contract_name="my_contract.pdf",
            )


# ---------------------------------------------------------------------------
# Node: evaluate_risk
# ---------------------------------------------------------------------------


class TestEvaluateRiskNode:
    """Verify parsing of risk level, executive summary, and clauses."""

    def test_success_extracts_high_risk(self):
        result = evaluate_risk(make_state(analysis=SAMPLE_CREW_OUTPUT))
        assert result["risk_level"] == "High"
        assert result["status"] == "evaluated"

    def test_success_extracts_executive_summary(self):
        result = evaluate_risk(make_state(analysis=SAMPLE_CREW_OUTPUT))
        assert "Alpha Corp" in result["executive_summary"]

    def test_success_extracts_clause_names(self):
        result = evaluate_risk(make_state(analysis=SAMPLE_CREW_OUTPUT))
        clauses = result["extracted_clauses"]
        assert isinstance(clauses, list)
        assert len(clauses) > 0
        # At least one recognisable clause name must be present
        clause_text = " ".join(clauses)
        assert any(name in clause_text for name in ("Payment", "Termination", "Confidentiality"))

    def test_low_risk_parsed_correctly(self):
        output = SAMPLE_CREW_OUTPUT.replace("OVERALL RISK RATING: High", "OVERALL RISK RATING: Low")
        result = evaluate_risk(make_state(analysis=output))
        assert result["risk_level"] == "Low"

    def test_medium_risk_parsed_correctly(self):
        output = SAMPLE_CREW_OUTPUT.replace("OVERALL RISK RATING: High", "OVERALL RISK RATING: Medium")
        result = evaluate_risk(make_state(analysis=output))
        assert result["risk_level"] == "Medium"

    def test_missing_risk_pattern_adds_error(self):
        result = evaluate_risk(make_state(analysis="No risk rating in this output."))
        assert result["risk_level"] == ""
        assert any("OVERALL RISK RATING" in e for e in result["errors"])
        assert result["status"] == "error"

    def test_unexpected_risk_value_adds_error(self):
        bad_output = SAMPLE_CREW_OUTPUT.replace("OVERALL RISK RATING: High", "OVERALL RISK RATING: Critical")
        result = evaluate_risk(make_state(analysis=bad_output))
        assert result["risk_level"] == ""
        assert any("Critical" in e for e in result["errors"])

    def test_guard_skips_when_errors_already_present(self):
        result = evaluate_risk(make_state(errors=["earlier failure"], analysis=SAMPLE_CREW_OUTPUT))
        # Should not have parsed anything — just returned the guard status
        assert result["status"] == "error"
        assert "risk_level" not in result or result.get("risk_level") == ""


# ---------------------------------------------------------------------------
# Node: save_report
# ---------------------------------------------------------------------------


class TestSaveReportNode:
    """Verify report path extraction."""

    def test_extracts_report_path_from_crew_output(self):
        result = save_report(make_state(analysis=SAMPLE_CREW_OUTPUT))
        assert "/home/user/contracts/reports/service_agreement_20250101_120000.md" in result["report_path"]
        assert result["status"] == "complete"

    def test_missing_path_falls_back_to_empty_string(self):
        result = save_report(make_state(analysis="No path here."))
        assert result["report_path"] == ""
        assert result["status"] == "complete"


# ---------------------------------------------------------------------------
# Node: handle_error
# ---------------------------------------------------------------------------


class TestHandleErrorNode:
    """Verify error status is set correctly."""

    def test_sets_status_to_error(self):
        state = make_state(errors=["load_contract failed: file not found"])
        result = handle_error(state)
        assert result["status"] == "error"

    def test_returns_only_status_update(self):
        state = make_state(errors=["err1", "err2"])
        result = handle_error(state)
        # handle_error should not add to errors (that is the accumulating nodes' job)
        assert "errors" not in result


# ---------------------------------------------------------------------------
# build_graph
# ---------------------------------------------------------------------------


class TestBuildGraph:
    """Verify the compiled graph structure."""

    def test_build_graph_returns_compiled_graph(self):
        graph = build_graph()
        assert graph is not None

    def test_compiled_graph_has_invoke_method(self):
        graph = build_graph()
        assert callable(getattr(graph, "invoke", None))

    def test_compiled_graph_exposes_expected_nodes(self):
        graph = build_graph()
        # LangGraph compiled graphs expose their node names via .nodes
        node_names = set(graph.nodes.keys())
        expected_nodes = {
            "load_contract",
            "run_contract_crew",
            "evaluate_risk",
            "save_report",
            "handle_error",
        }
        assert expected_nodes.issubset(node_names), (
            f"Missing nodes: {expected_nodes - node_names}"
        )
