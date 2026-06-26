"""
crew/__init__.py
----------------
Public interface for the crew package.

External callers (the LangGraph workflow in graph/workflow.py) should import
ContractCrew from here. Internal modules (agents, tasks) are implementation
details and should not be imported from outside the crew package directly.

Usage:
    from crew import ContractCrew

    crew = ContractCrew(file_path="...", contract_name="...")
    report = crew.run()
"""

from crew.contract_crew import ContractCrew

__all__ = ["ContractCrew"]
