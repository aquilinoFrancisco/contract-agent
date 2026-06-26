"""
graph/__init__.py
-----------------
Public interface for the graph package.

External callers (the Streamlit UI in app/main_app.py) should import
build_graph and initial_state from here. Internal node functions are
implementation details.

Usage:
    from graph import build_graph, initial_state

    graph = build_graph()
    result = graph.invoke(initial_state("/path/to/contract.pdf"))
"""

from graph.state import ContractState, initial_state
from graph.workflow import build_graph

__all__ = ["build_graph", "initial_state", "ContractState"]
