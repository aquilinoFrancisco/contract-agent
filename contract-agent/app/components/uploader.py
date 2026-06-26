"""
app/components/uploader.py
--------------------------
File Uploader Component

Responsibility:
    Render the Streamlit file uploader, persist the uploaded bytes to the
    contracts/ directory, and return the saved file path to the caller.

    All file-system interaction is isolated here. main_app.py only receives
    a path string — it never touches bytes or file handles directly.

Design decisions:
    - Returns str | None so main_app.py can check truthiness before enabling
      the Analyse button. None means "no file selected yet".
    - Saves to settings.contracts_dir (not a temp dir) so the CrewAI layer
      and MCP tools can read the file by path without any copy step.
    - Overwrites silently if the same filename is uploaded again — acceptable
      for a single-user demo tool; a multi-user deployment would add a UUID prefix.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from config.settings import settings


def render_uploader() -> str | None:
    """
    Render the contract file uploader widget.

    Saves the uploaded file to contracts/ and stores the path in
    st.session_state["contract_path"].

    Returns:
        Absolute path to the saved file as a string, or None if no file
        has been selected.
    """
    st.subheader("📁 Upload Contract")
    st.caption("Accepts PDF and TXT files up to 10 MB.")

    uploaded = st.file_uploader(
        label="Choose a contract file",
        type=["pdf", "txt"],
        label_visibility="collapsed",
        help="Drag and drop or click to browse. PDF and TXT files supported.",
    )

    if uploaded is None:
        # Preserve the previously uploaded path across Streamlit reruns.
        return st.session_state.get("contract_path")

    # Ensure the contracts directory exists before writing.
    settings.contracts_dir.mkdir(parents=True, exist_ok=True)

    save_path = settings.contracts_dir / uploaded.name
    save_path.write_bytes(uploaded.getvalue())

    # Persist in session state so the path survives page reruns.
    st.session_state["contract_path"] = str(save_path)

    file_size_kb = round(len(uploaded.getvalue()) / 1024, 1)
    st.success(f"✅ **{uploaded.name}** uploaded ({file_size_kb} KB)")

    return str(save_path)
