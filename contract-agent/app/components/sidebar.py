"""
app/components/sidebar.py
-------------------------
Sidebar Component

Responsibility:
    Render the application sidebar containing:
        1. Pipeline status and progress bar
        2. Project architecture diagram
        3. How-to-use instructions

    Reads from st.session_state — never modifies it.

Design decisions:
    - Status labels map 1:1 to ContractState["status"] values so the sidebar
      accurately reflects the graph's lifecycle without additional translation.
    - Progress values are deterministic estimates, not real-time updates.
      LangGraph's graph.invoke() is synchronous — there is no hook to update
      progress mid-run. The spinner in main_app.py covers the wait period.
    - The architecture diagram is plain text (Markdown code block) so it
      renders identically in any Streamlit theme. No image assets needed.
"""

from __future__ import annotations

import streamlit as st

# Map ContractState["status"] values to (label, progress 0.0–1.0)
_STATUS_MAP: dict[str, tuple[str, float]] = {
    "pending":          ("⏳ Waiting to start",      0.00),
    "contract_loaded":  ("📂 Contract loaded",       0.20),
    "crew_running":     ("🤖 AI agents running…",    0.50),
    "crew_complete":    ("✅ Agents complete",        0.70),
    "evaluated":        ("🔍 Risk evaluated",         0.85),
    "complete":         ("🎉 Analysis complete",      1.00),
    "error":            ("❌ Error occurred",          1.00),
}


def render_sidebar() -> None:
    """Render the full application sidebar."""
    with st.sidebar:
        st.title("Contract Agent")
        st.caption("AI-powered legal analysis")

        st.divider()

        # --------------------------------------------------------------
        # Pipeline status + progress bar
        # --------------------------------------------------------------
        st.markdown("### 📡 Pipeline Status")

        current_step: str = st.session_state.get("current_step", "pending")
        label, progress = _STATUS_MAP.get(
            current_step, (f"Status: {current_step}", 0.0)
        )
        st.markdown(f"**{label}**")

        # Colour the progress bar for error state vs normal state.
        if current_step == "error":
            st.progress(1.0)
            st.markdown(":red[See error details in the main panel.]")
        else:
            st.progress(progress)

        st.divider()

        # --------------------------------------------------------------
        # Architecture overview
        # --------------------------------------------------------------
        st.markdown("### 🏗️ Architecture")
        st.markdown(
            """
```
Streamlit (UI)
    ↓  invoke(state)
LangGraph (orchestration)
    ↓  load → crew → evaluate
CrewAI (3 agents)
    ├─ ContractReader
    ├─ LegalAnalyst
    └─ ExecutiveSummarizer
        ↓  tool calls
MCP (3 tools)
    ├─ read_file
    ├─ search_clause
    └─ save_report
```
"""
        )

        st.divider()

        # --------------------------------------------------------------
        # How to use
        # --------------------------------------------------------------
        st.markdown("### 📖 How to Use")
        st.markdown(
            """
1. **Upload** a PDF or TXT contract
2. Click **Analyse Contract**
3. Review the executive summary and risk rating
4. Expand the full report for detail
"""
        )

        # --------------------------------------------------------------
        # API key warning (always visible — non-blocking)
        # --------------------------------------------------------------
        from config.settings import settings  # local import avoids circular risk

        if not settings.openai_api_key:
            st.divider()
            st.warning(
                "⚠️ **OPENAI_API_KEY not set.**\n\n"
                "Analysis will fail at the AI step. "
                "Add it to your `.env` file and restart the app."
            )
