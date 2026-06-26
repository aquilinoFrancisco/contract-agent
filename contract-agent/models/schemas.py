"""
models/schemas.py
-----------------
Shared Pydantic v2 data models for the Contract Agent.

Responsibility:
    Single source of truth for every structured data type that crosses a
    boundary between modules — between agents, between the graph nodes, and
    between the MCP tools and the crew.

    Defining models here (rather than inline in each module) enforces a shared
    vocabulary and makes inter-module contracts explicit and type-checked.

Design note:
    All models use Pydantic v2 (`model_config`, `model_validator`, etc.).
    LangGraph state schema is defined in graph/state.py, not here, because
    it uses TypedDict rather than BaseModel.

Models to be implemented in Phase 3:
    - ContractFile      : metadata about an uploaded contract file
    - ExtractionResult  : structured output from the ContractReader agent
    - AnalysisResult    : structured output from the LegalAnalyst agent
    - FinalReport       : structured output from the ExecutiveSummarizer agent
    - RiskLevel         : Enum — Low / Medium / High
    - Clause            : a single identified clause (name, content, risk)
    - Obligation        : a single party obligation (party, description, deadline)
"""

from __future__ import annotations

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Placeholder — models to be added in Phase 3
# ---------------------------------------------------------------------------


class ContractFile(BaseModel):
    """Metadata about an uploaded contract file."""
    pass


class ExtractionResult(BaseModel):
    """Structured output produced by the ContractReader agent."""
    pass


class AnalysisResult(BaseModel):
    """Structured output produced by the LegalAnalyst agent."""
    pass


class FinalReport(BaseModel):
    """Structured output produced by the ExecutiveSummarizer agent."""
    pass
