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
