"""
app/main_app.py
---------------
Contract Agent — Streamlit Application Entry Point

Responsibility:
    Orchestrate the UI flow. This file:
        1. Initialises session state
        2. Renders the sidebar, uploader, and results components
        3. Calls build_graph() and graph.invoke() when the user triggers analysis
        4. Passes the resulting ContractState to the results component

    No contract analysis logic lives here. All agent processing is inside
    the LangGraph workflow (graph/workflow.py) and the CrewAI crew (crew/).

Run:
    cd contract-agent
    streamlit run app/main_app.py

Architecture (data flow):
    User uploads file → uploader.py saves it → main_app calls graph.invoke()
    → LangGraph nodes run → ContractCrew runs CrewAI → results stored in state
    → results.py renders state → sidebar.py reflects current_step

Session state keys:
    contract_path   str | None   Path to the saved contract file
    graph_result    dict | None  Full ContractState after graph.invoke()
    current_step    str          Maps to ContractState["status"] values
    progress        float        0.0–1.0 progress bar value
    errors          list[str]    Errors surfaced from the graph result
"""

from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path bootstrap — ensures project root is importable regardless of where
# Streamlit is launched from. Must come before any project-local imports.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Standard imports (after path fix)
# ---------------------------------------------------------------------------
import streamlit as st

from app.components.results import render_results
from app.components.sidebar import render_sidebar
from app.components.uploader import render_uploader
from graph import build_graph, initial_state

# ---------------------------------------------------------------------------
# Page configuration — must be the first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Contract Agent",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Graph — compiled once per app process, reused across reruns
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def get_graph():
    """
    Compile and cache the LangGraph graph.

    @st.cache_resource caches the return value across all user sessions and
    Streamlit reruns for the lifetime of the server process. Compiling the
    graph (which just wires Python functions together) is cheap, but caching
    it avoids re-running graph.compile() on every rerun, keeping the UI snappy.
    """
    return build_graph()


# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------

def _init_session_state() -> None:
    """Initialise session state keys with safe defaults on first load."""
    defaults: dict = {
        "contract_path": None,   # str path to the uploaded file
        "graph_result": None,    # ContractState dict after graph.invoke()
        "current_step": "pending",
        "progress": 0.0,
        "errors": [],
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


_init_session_state()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

render_sidebar()


# ---------------------------------------------------------------------------
# Main panel
# ---------------------------------------------------------------------------

st.title("📄 Contract Agent")
st.caption(
    "AI-powered legal contract analysis · "
    "**LangGraph** orchestration · **CrewAI** agents · **MCP** tools"
)

st.divider()

# Two-column layout: upload on the left, results on the right
left_col, right_col = st.columns([1, 2], gap="large")

with left_col:
    # ------------------------------------------------------------------
    # File uploader — returns path or None
    # ------------------------------------------------------------------
    contract_path = render_uploader()

    st.divider()

    # ------------------------------------------------------------------
    # Analyse button
    # ------------------------------------------------------------------
    analyse_ready = contract_path is not None
    btn_label = "🔍 Analyse Contract" if analyse_ready else "Upload a file to start"

    if st.button(
        btn_label,
        type="primary",
        use_container_width=True,
        disabled=not analyse_ready,
    ):
        # Reset previous results before a new run
        st.session_state["graph_result"] = None
        st.session_state["errors"] = []
        st.session_state["current_step"] = "pending"
        st.session_state["progress"] = 0.0

        graph = get_graph()
        state = initial_state(contract_path)

        # All graph processing runs inside a spinner so the user has feedback.
        with st.spinner("🤖 Running AI analysis pipeline… this may take a minute."):
            try:
                result: dict = graph.invoke(state)
                st.session_state["graph_result"] = result
                st.session_state["current_step"] = result.get("status", "complete")
                st.session_state["errors"] = result.get("errors", [])

                # Set progress to 1.0 regardless of status — the graph finished.
                st.session_state["progress"] = 1.0

            except Exception as exc:
                # Catch unexpected exceptions (network errors, import errors, etc.)
                # and show a friendly message instead of a full traceback.
                error_msg = str(exc)

                # Surface a specific, actionable message for the most common failure.
                if "api_key" in error_msg.lower() or "openai" in error_msg.lower():
                    friendly = (
                        "OpenAI API key is missing or invalid. "
                        "Add OPENAI_API_KEY to your .env file and restart the app."
                    )
                elif "rate" in error_msg.lower():
                    friendly = "OpenAI rate limit hit. Wait a moment and try again."
                else:
                    friendly = f"Unexpected error: {error_msg}"

                st.session_state["errors"] = [friendly]
                st.session_state["current_step"] = "error"
                st.session_state["progress"] = 1.0

        # Rerun so sidebar reflects updated current_step immediately.
        st.rerun()

with right_col:
    # ------------------------------------------------------------------
    # Results panel
    # ------------------------------------------------------------------
    if st.session_state["graph_result"] is not None:
        render_results(st.session_state["graph_result"])
    elif st.session_state["errors"]:
        # Errors that occurred before graph_result was set (e.g. exception catch above)
        st.error("❌ Analysis failed")
        for err in st.session_state["errors"]:
            st.markdown(f"- {err}")
    else:
        # Empty state — guide the user
        st.markdown(
            """
            ### Getting started

            1. **Upload** a PDF or TXT contract on the left
            2. Click **Analyse Contract**
            3. The AI pipeline will:
               - Extract the contract structure
               - Identify clauses, risks, and obligations
               - Generate a plain-language executive report

            The analysis typically takes 60–120 seconds depending on contract length.

            ---
            **Demo tip:** No contract to hand? Create a simple `.txt` file with a
            short agreement and upload it to see the full pipeline in action.
            """
        )
