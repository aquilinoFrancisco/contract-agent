"""
models/schemas.py
-----------------
Shared Pydantic v2 data models for the Contract Agent.

Responsibility:
    Single source of truth for every structured data type that crosses a
    module boundary — between agents, between graph nodes, and between the
    MCP tools and the crew.

    Defining models here enforces a shared vocabulary: if the LegalAnalyst
    produces an AnalysisResult and the ExecutiveSummarizer expects one, both
    import from this file. There is no risk of the two sides drifting apart.

Design decisions:
    - All models are Pydantic v2 BaseModel. They do not inherit from each
      other (no inheritance chains) — composition is used instead.
    - RiskLevel is a str Enum so it serialises naturally to JSON ("Low",
      "Medium", "High") without a custom encoder.
    - All Optional fields default to None or empty list, never to mutable
      default objects (Pydantic handles this safely via Field(default_factory)).
    - LangGraph state is defined in graph/state.py (TypedDict), not here.
      These Pydantic models are for validated, structured agent outputs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class RiskLevel(str, Enum):
    """
    Risk severity classification used across agents and reports.

    Using str Enum means values serialise as plain strings ("Low", "Medium",
    "High") in JSON — no custom encoder needed, and the values are readable
    in the raw report files.
    """

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------


class Clause(BaseModel):
    """
    A single identified clause extracted from a contract.

    Produced by: LegalAnalyst
    Consumed by: ExecutiveSummarizer, FinalReport, Streamlit UI
    """

    name: str = Field(..., description="Clause name, e.g. 'Payment Terms', 'Termination'.")
    content: str = Field(..., description="The verbatim or paraphrased clause text.")
    risk_level: RiskLevel = Field(
        default=RiskLevel.LOW,
        description="Risk assessment for this specific clause.",
    )
    notes: str = Field(
        default="",
        description="Analyst commentary — why this clause is noteworthy or risky.",
    )


class Obligation(BaseModel):
    """
    A single contractual obligation assigned to a specific party.

    Produced by: LegalAnalyst
    Consumed by: ExecutiveSummarizer, FinalReport
    """

    party: str = Field(..., description="The party who bears this obligation.")
    description: str = Field(..., description="What the party must do or refrain from doing.")
    deadline: str | None = Field(
        default=None,
        description="Deadline or trigger event, if specified. None if open-ended.",
    )


# ---------------------------------------------------------------------------
# Agent output models
# ---------------------------------------------------------------------------


class ContractFile(BaseModel):
    """
    Metadata and content of an uploaded contract file.

    Produced by: MCP read_file tool (via ContractReader)
    Consumed by: LangGraph state, reading_task description
    """

    file_path: str = Field(..., description="Absolute path to the contract file on disk.")
    file_name: str = Field(..., description="Original filename, e.g. 'service_agreement.pdf'.")
    format: str = Field(..., description="File format: 'pdf' or 'txt'.")
    text: str = Field(..., description="Full plain-text content of the contract.")


class ExtractionResult(BaseModel):
    """
    Structured output produced by the ContractReader agent.

    Contains the raw structural information extracted from the contract —
    no legal analysis, no interpretation.

    Produced by: ContractReader (reading_task)
    Consumed by: LegalAnalyst via task context
    """

    contract_type: str = Field(
        ...,
        description="Type of contract, e.g. 'NDA', 'Service Agreement', 'Employment Contract'.",
    )
    parties: list[str] = Field(
        default_factory=list,
        description="All named parties in the contract.",
    )
    effective_date: str | None = Field(
        default=None,
        description="The contract's effective/start date, if explicitly stated.",
    )
    expiry_date: str | None = Field(
        default=None,
        description="The contract's end/expiry date, if stated.",
    )
    key_dates: list[str] = Field(
        default_factory=list,
        description="All dates mentioned in the contract (deadlines, notice periods, etc.).",
    )
    section_headings: list[str] = Field(
        default_factory=list,
        description="All section or article headings found in the document.",
    )
    governing_law: str | None = Field(
        default=None,
        description="Jurisdiction or governing law clause, if present.",
    )


class AnalysisResult(BaseModel):
    """
    Structured output produced by the LegalAnalyst agent.

    Contains the legal interpretation layered on top of the extraction —
    clauses classified, risks rated, obligations itemised.

    Produced by: LegalAnalyst (analysis_task)
    Consumed by: ExecutiveSummarizer via task context
    """

    clauses: list[Clause] = Field(
        default_factory=list,
        description="All identified clauses with risk ratings and analyst notes.",
    )
    red_flags: list[str] = Field(
        default_factory=list,
        description="Unusual, missing, or one-sided provisions that warrant attention.",
    )
    obligations: list[Obligation] = Field(
        default_factory=list,
        description="All obligations found, assigned to their responsible parties.",
    )
    overall_risk: RiskLevel = Field(
        default=RiskLevel.MEDIUM,
        description="Overall risk rating for the entire contract.",
    )
    missing_clauses: list[str] = Field(
        default_factory=list,
        description="Standard clauses that are absent from this contract (e.g. 'No liability cap').",
    )


class FinalReport(BaseModel):
    """
    Structured output produced by the ExecutiveSummarizer agent.

    This is the user-facing deliverable: a complete, plain-language analysis
    report ready to be rendered by the Streamlit UI or saved to disk.

    Produced by: ExecutiveSummarizer (summary_task)
    Consumed by: Streamlit UI, save_report MCP tool
    """

    contract_name: str = Field(..., description="Name of the source contract file.")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of when the report was generated.",
    )
    executive_summary: str = Field(
        ...,
        description="3–5 sentence plain-language overview of the contract.",
    )
    key_clauses: list[Clause] = Field(
        default_factory=list,
        description="The most important clauses, explained in plain language.",
    )
    risks: list[str] = Field(
        default_factory=list,
        description="Prioritised list of risks and red flags (highest risk first).",
    )
    obligations: list[Obligation] = Field(
        default_factory=list,
        description="Plain-language obligations for each party.",
    )
    key_dates: list[str] = Field(
        default_factory=list,
        description="All important dates and deadlines in chronological order.",
    )
    overall_risk: RiskLevel = Field(
        ...,
        description="Top-level risk rating for the contract.",
    )
    recommendation: str = Field(
        ...,
        description="One-sentence actionable recommendation for the reader.",
    )
