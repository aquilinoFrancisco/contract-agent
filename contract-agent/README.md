# Contract Agent

An AI-powered legal contract analysis tool built as a portfolio project to demonstrate modern AI Agent architecture.

## What It Does

Upload a PDF or TXT contract and receive a structured analysis in seconds:

- **Executive Summary** — plain-language overview of the contract
- **Important Clauses** — key provisions extracted and explained
- **Potential Risks & Red Flags** — unusual or dangerous terms highlighted
- **Obligations** — what each party must do
- **Key Dates** — deadlines, renewal windows, termination notices

## Architecture

```
Streamlit UI (app/)
    │
    ▼
LangGraph Workflow (graph/)        ← orchestrates the pipeline
    │
    ├── ContractReader Agent   ──┐
    ├── LegalAnalyst Agent     ──┤  CrewAI (crew/)
    └── ExecutiveSummarizer    ──┘
              │
              ▼
        MCP Tools (mcp/)           ← read_file · search_clause · save_report
              │
    ┌─────────┴──────────┐
contracts/ (input)    reports/ (output)
```

### Key Design Decisions

| Decision | Rationale |
|---|---|
| LangGraph as orchestrator | Provides explicit, inspectable state + conditional edges — not a black box |
| CrewAI for agents | Role-based agents with clear separation of concerns (reader → analyst → summarizer) |
| MCP for tools | Decouples tool implementation from agent logic; MCP is the emerging standard |
| Streamlit as UI | Zero-friction UI for data-heavy AI apps; keeps the demo self-contained |
| `pyproject.toml` | Modern Python packaging standard (PEP 621); replaces legacy `requirements.txt` |

## Project Structure

```
contract-agent/
├── app/
│   ├── main_app.py          # Streamlit entry point
│   ├── components/          # Reusable Streamlit widgets
│   └── styles/              # CSS overrides (if needed)
├── graph/
│   ├── state.py             # TypedDict graph state schema
│   └── workflow.py          # LangGraph graph with conditional edges
├── crew/
│   ├── contract_reader.py   # Agent 1 — extracts raw text and structure
│   ├── legal_analyst.py     # Agent 2 — identifies clauses, risks, obligations
│   ├── executive_summarizer.py  # Agent 3 — produces executive output
│   ├── reading_task.py      # Task for ContractReader
│   ├── analysis_task.py     # Task for LegalAnalyst
│   ├── summary_task.py      # Task for ExecutiveSummarizer
│   └── contract_crew.py     # Wires agents + tasks into a Crew
├── mcp/
│   ├── server.py            # MCP server definition
│   └── tools/
│       ├── read_file.py     # Tool: read contract from disk
│       ├── search_clause.py # Tool: search for a specific clause
│       └── save_report.py   # Tool: persist analysis report
├── contracts/               # Drop-zone for uploaded contracts (gitignored)
├── reports/                 # Generated reports (gitignored)
├── tests/
│   ├── test_agents.py
│   ├── test_graph.py
│   └── test_mcp.py
├── pyproject.toml
└── README.md
```

## Setup

### Prerequisites

- Python 3.11+
- An OpenAI API key

### Install

```bash
git clone <repo-url>
cd contract-agent

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -e ".[dev]"
```

### Configure

```bash
cp .env.example .env
# Add your OPENAI_API_KEY to .env
```

### Run

```bash
streamlit run app/main_app.py
```

Open `http://localhost:8501` in your browser.

## Running Tests

```bash
pytest tests/
```

## Tech Stack

| Layer | Technology |
|---|---|
| UI | Streamlit |
| Orchestration | LangGraph |
| Agents | CrewAI |
| Tools | Model Context Protocol (MCP) |
| LLM | OpenAI GPT-4o |
| PDF Parsing | pypdf |
| Validation | Pydantic v2 |
| Language | Python 3.11 |
