# Interview Notes

Talking points, design rationale, and answers to common technical interview questions about the Contract Agent project.

---

## Why LangGraph instead of a simple chain?

**The short answer:** A simple chain is a straight line. LangGraph is a graph — it can branch, loop, and make decisions based on state.

**Talking points:**

- **Explicit state management.** LangGraph forces you to define a `TypedDict` state schema upfront. Every node reads from and writes to that schema. There are no hidden variables passing between steps — an interviewer can look at the state and know exactly what data is in flight at any point in the pipeline.

- **Conditional edges.** A chain always goes A → B → C. LangGraph lets you write a routing function that inspects the current state and decides which node to execute next. In Contract Agent, if the document parser returns an error, the graph routes to an error-handling node instead of blindly continuing to the agents.

- **Inspectability.** LangGraph graphs can be visualised as a directed graph (nodes + edges). This makes the architecture tangible in a code review or architecture discussion — you can literally draw the flow.

- **Resilience to partial failures.** Because state is explicit and edges are conditional, you can checkpoint state mid-graph and resume from a failure point without rerunning successful nodes. LangChain's `LCEL` chains have no such native mechanism.

- **Production readiness.** LangGraph is the recommended orchestration layer in LangChain's own documentation for "agentic" workloads. Choosing it signals awareness of the current ecosystem.

**What to avoid saying:** "I used LangGraph because it was trendy." Instead, tie every point back to a concrete problem it solves — state visibility, branching, recoverability.

---

## Why CrewAI with 3 agents instead of one?

**The short answer:** One agent doing everything produces one large, unfocused prompt with no separation of concerns. Three agents with distinct roles produce higher-quality output through specialisation.

**Talking points:**

- **Single Responsibility at the AI level.** Each agent has one job:
  - `ContractReader` — extract structure and raw text. Its system prompt is tuned for extraction, not analysis.
  - `LegalAnalyst` — identify clauses, risks, and obligations. Its system prompt is tuned for legal reasoning.
  - `ExecutiveSummarizer` — translate legal findings into plain business language. Its system prompt is tuned for clarity and concision.
  Mixing all three into one agent produces a muddy prompt that attempts to do everything and excels at nothing.

- **Context window efficiency.** A single all-in-one agent receives the full contract text plus all analysis instructions in one prompt. With three agents, each receives only what it needs. The summarizer, for example, never sees the raw contract — it only receives the analyst's structured output, which is much shorter and more focused.

- **Auditability.** Because each agent produces its own output, you can inspect what the reader extracted vs. what the analyst concluded vs. what the summarizer wrote. If the final report is wrong, you can trace exactly which agent introduced the error.

- **Replaceability.** You can swap one agent's LLM or prompt without touching the others. You could run `ContractReader` on GPT-4o-mini (cheap, good at extraction) and `LegalAnalyst` on GPT-4o (expensive, better at reasoning) — a cost/quality trade-off that a single-agent design cannot make.

**Follow-up you may hear:** *"Couldn't you achieve the same thing with three sequential prompts without CrewAI?"* Answer: Yes — but CrewAI adds task dependency management, context passing between agents, and a higher-level abstraction that makes the code more maintainable and the system easier to extend.

---

## Why MCP for tool exposure?

**The short answer:** MCP is the emerging standard for connecting AI agents to external tools. It separates *what the tool does* from *how the agent calls it* — the same interface every agent framework can speak.

**Talking points:**

- **Decoupling by design.** Without MCP, tool functions are imported directly into your agent or crew. Every agent framework has its own decorator or wrapper format (`@tool`, `BaseTool`, etc.). With MCP, the tools are defined once in a server; any MCP-compatible client — CrewAI, LangGraph, Claude, a future framework — can discover and call them via a standard JSON-RPC protocol without any code changes to the tools themselves.

- **Discoverability.** An MCP server exposes a `list_tools` endpoint. Clients call it at runtime to learn what tools are available, their names, descriptions, and input schemas. This means you can add a new tool to the server and every client picks it up without redeployment.

- **Reusability across projects.** The `read_file`, `search_clause`, and `save_report` tools in this project can be reused by any other MCP-compatible agent with zero changes. They are infrastructure, not application code.

- **Testability.** Because MCP tools are pure functions wrapped by a server, they can be tested entirely independently of any LLM or agent framework. The 52-test suite in this project tests tools directly without spinning up a CrewAI crew or a LangGraph graph.

- **Industry direction.** MCP was introduced by Anthropic in late 2024 and has been adopted by OpenAI, Google DeepMind, and major IDE vendors. Choosing it signals that you track the ecosystem and build for longevity, not just for today.

**What to avoid saying:** "MCP is the same as function calling." It is not — function calling is a model-level feature for a specific LLM. MCP is a transport-level protocol that works across models, frameworks, and languages.

---

## What does the conditional edge in LangGraph do?

**In this project:** After the document is parsed by `read_file`, a conditional edge inspects the result. If the result contains a non-empty `text` field, the graph routes forward to the CrewAI crew node. If the result is empty or contains an error, the graph routes to an error node that returns a structured failure message to the Streamlit UI.

**Why this matters:**

- It prevents the agents from receiving an empty or garbage input, which would cause them to hallucinate content about a non-existent contract.
- It gives users immediate, actionable feedback ("Could not read this file — please check the format") instead of a confusing LLM-generated response about nothing.
- It demonstrates that the pipeline has real decision logic, not just a straight-line sequence of prompts.

**How to explain it in an interview:**

> "The conditional edge is a routing function that takes the current graph state and returns the name of the next node. It's just a Python function — `if state['text']: return 'run_crew'` else `return 'handle_error'`. What makes it powerful is that this decision is explicit, typed, and testable, rather than buried inside a prompt."

---

## How do the agents pass context to each other?

**Mechanism:** CrewAI tasks are chained via `context` parameter. Each task declares which upstream tasks it depends on, and CrewAI passes those tasks' outputs as context into the next task's prompt automatically.

```
reading_task   → output: raw extracted text + structure
     ↓ (passed as context)
analysis_task  → output: clauses, risks, obligations (structured)
     ↓ (passed as context)
summary_task   → output: executive report (plain language)
```

**Talking points:**

- The `ContractReader`'s output becomes part of the `LegalAnalyst`'s prompt context — the analyst never calls `read_file` directly.
- The `LegalAnalyst`'s structured findings become part of the `ExecutiveSummarizer`'s prompt — the summarizer never sees the raw contract text.
- This is a deliberate information-hiding pattern: each agent only sees the abstraction level it needs. It keeps prompts short and focused.
- All three agents' outputs are also accumulated in the LangGraph state dict, so the Streamlit UI can display each agent's individual output as well as the final report.

---

## Common "why did you choose X?" questions

### Why Python 3.11?
3.11 introduced significant performance improvements (10–60% faster than 3.10 in benchmarks) and better error messages. It is also the current stable target for LangGraph, CrewAI, and the MCP SDK. Using 3.12+ would risk compatibility issues with some of these libraries.

### Why Streamlit and not FastAPI + React?
For an AI portfolio project, Streamlit is the right tool. The goal is to demonstrate AI Agent architecture, not frontend engineering. Streamlit eliminates the frontend entirely so the code stays focused on the intelligence layer. A FastAPI + React version would double the codebase size while adding no insight into the AI design.

### Why OpenAI GPT-4o?
GPT-4o has strong legal text comprehension, a large context window (128k tokens) that can fit most real-world contracts, and is the reference model for most agent frameworks. The architecture is LLM-agnostic — swapping to Claude or Gemini requires changing one config value.

### Why pypdf and not PyMuPDF?
pypdf is pure Python, zero system dependencies, and Apache-licensed. PyMuPDF (fitz) is faster and handles more complex PDFs but requires native MuPDF binaries and has a more restrictive license. For a portfolio project handling standard legal PDFs, pypdf is the right size.

### Why pyproject.toml and not requirements.txt?
`pyproject.toml` (PEP 621) is the modern Python packaging standard. It collocates project metadata, dependencies, and tool configuration (black, isort, mypy, pytest) in one file. Using it signals familiarity with current Python tooling conventions.

---

## What would you improve with more time?

Be specific — vague answers like "add more features" are weak. These are concrete, architecturally-grounded improvements:

1. **Streaming output.** Right now the UI shows nothing until all three agents finish. With LangGraph's streaming support and Streamlit's `st.write_stream`, you could stream each agent's output token-by-token as it's produced. This makes the UX dramatically better for long contracts.

2. **Persistent state with LangGraph checkpointing.** LangGraph supports pluggable checkpointers (SQLite, PostgreSQL). Adding one would allow resuming an interrupted analysis and storing a history of past analyses — a foundation for a real product.

3. **Structured output from agents.** Currently agents return free-text. Replacing free-text with Pydantic models (using CrewAI's `output_pydantic` parameter) would make downstream parsing reliable and testable, and would enable programmatic filtering (e.g., "show only high-severity risks").

4. **A vector store for clause search.** The current `search_clause` tool does naive keyword matching. Adding a vector embedding store (Chroma, Qdrant) would enable semantic search — "find clauses related to liability" — even when the exact word "liability" doesn't appear.

5. **Evaluation harness.** There is no automated way to know if the analysis quality regressed after a prompt change. Adding an eval suite with a set of known contracts and expected outputs (using a framework like LangSmith or Ragas) would turn prompt engineering from guesswork into a measurable process.

6. **Multi-document comparison.** The current design handles one contract at a time. Extending the LangGraph state to hold multiple contracts and adding a comparison agent would turn this from a single-document tool into a contract negotiation assistant.

---

## One-sentence summary for each technology

Use these when asked to explain the stack quickly:

| Technology | One-sentence pitch |
|---|---|
| **LangGraph** | A graph-based orchestrator that makes AI pipelines explicit, inspectable, and capable of conditional branching — not a black-box chain. |
| **CrewAI** | A multi-agent framework that lets you assign distinct roles, prompts, and tasks to specialised agents and wire their outputs together. |
| **MCP** | An open protocol for exposing tools to AI agents in a framework-agnostic, discoverable way — the same tool server can serve any MCP-compatible client. |
| **Streamlit** | A Python-native UI framework that turns data and AI pipelines into interactive web apps with minimal frontend code. |
| **pypdf** | A pure-Python PDF parser that extracts text from contracts without native dependencies or license complications. |
| **Pydantic v2** | A data validation library that enforces types at runtime — used to keep the LangGraph state schema honest. |
