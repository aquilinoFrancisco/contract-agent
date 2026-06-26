"""
app/components/results.py
-------------------------
Results Display Component

Responsibility:
    Render the full contract analysis output from the LangGraph result state.
    Displays executive summary, risk level, key clauses, report path, and
    any errors. Pulls data from the ContractState dict — no business logic.

Design decisions:
    - Accepts ContractState (a plain dict at runtime) so this component is
      decoupled from LangGraph internals. It reads keys by name, not by type.
    - Risk level is rendered with colour-coded Streamlit alerts (success /
      warning / error) rather than raw text so the demo reads at a glance.
    - The full crew report is shown in an expander so the summary is visible
      immediately without scrolling. Interviewers can expand for depth.
    - Errors are always rendered first. If the pipeline failed, the user
      should see why before seeing any partial results.
"""

from __future__ import annotations

import streamlit as st


# Map risk level strings to (Streamlit colour, emoji) for display.
_RISK_STYLE: dict[str, tuple[str, str]] = {
    "Low":    ("success", "🟢"),
    "Medium": ("warning", "🟡"),
    "High":   ("error",   "🔴"),
}


def render_results(state: dict) -> None:
    """
    Render the full analysis results panel.

    Args:
        state: The ContractState dict returned by graph.invoke(). Expected
               keys: executive_summary, risk_level, extracted_clauses,
               report_path, analysis, errors, status.
    """
    st.divider()
    st.subheader("📋 Analysis Results")

    # ------------------------------------------------------------------
    # Errors — always shown first so failures are obvious
    # ------------------------------------------------------------------
    errors: list[str] = state.get("errors", [])
    if errors:
        st.error("⚠️ The pipeline encountered errors:")
        for err in errors:
            st.markdown(f"- `{err}`")
        # Still render any partial results below if they exist.
        if not state.get("executive_summary") and not state.get("analysis"):
            return

    # ------------------------------------------------------------------
    # Status banner
    # ------------------------------------------------------------------
    status = state.get("status", "")
    if status == "complete":
        st.success("✅ Analysis complete")
    elif status == "error":
        st.error("❌ Analysis failed — see errors above")
    else:
        st.info(f"Pipeline status: `{status}`")

    # ------------------------------------------------------------------
    # Overall Risk Level
    # ------------------------------------------------------------------
    risk_level = state.get("risk_level", "")
    if risk_level:
        alert_type, emoji = _RISK_STYLE.get(risk_level, ("info", "⚪"))
        st.markdown("#### Overall Risk Rating")
        getattr(st, alert_type)(f"{emoji} **{risk_level} Risk**")

    # ------------------------------------------------------------------
    # Executive Summary
    # ------------------------------------------------------------------
    executive_summary = state.get("executive_summary", "").strip()
    if executive_summary:
        st.markdown("#### 📝 Executive Summary")
        st.markdown(executive_summary)

    # ------------------------------------------------------------------
    # Key Clauses
    # ------------------------------------------------------------------
    clauses: list[str] = state.get("extracted_clauses", [])
    if clauses:
        st.markdown("#### 📌 Key Clauses Identified")
        cols = st.columns(min(len(clauses), 3))
        for i, clause in enumerate(clauses):
            with cols[i % len(cols)]:
                st.markdown(f"**{clause.strip()}**")

    # ------------------------------------------------------------------
    # Full Report (expandable)
    # ------------------------------------------------------------------
    full_report = state.get("analysis", "").strip()
    if full_report:
        with st.expander("📄 View Full Executive Report", expanded=False):
            st.markdown("```\n" + full_report + "\n```")

    # ------------------------------------------------------------------
    # Saved Report Path
    # ------------------------------------------------------------------
    report_path = state.get("report_path", "").strip()
    if report_path:
        st.info(f"💾 Report saved to: `{report_path}`")
    elif status == "complete":
        st.caption("Report path not detected in output — check the reports/ directory.")
