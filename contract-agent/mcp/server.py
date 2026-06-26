"""
mcp/server.py
-------------
MCP Server — Contract Agent

Responsibility:
    Define and run the Model Context Protocol server that exposes three tools
    to any MCP-compatible client (LangChain, CrewAI, LangGraph, etc.).

    Registered tools:
        1. read_file      — reads a PDF or TXT contract from disk
        2. search_clause  — keyword search with surrounding context
        3. save_report    — persists a finished analysis report

Design principles (SOLID):
    - Single Responsibility: this file owns protocol setup and request routing
      only — zero business logic lives here.
    - Open/Closed: adding a new tool requires (a) importing its function,
      (b) appending one Tool definition to TOOLS, and (c) adding one branch
      in _dispatch — the handler itself never changes.
    - Dependency Inversion: tool functions are imported from the tools/
      subpackage; the server depends on abstractions (the dict contract), not
      on their internals.

Communication model:
    The server speaks the MCP wire protocol over stdio (stdin/stdout).
    Clients discover available tools via the list_tools RPC, then invoke
    them via call_tool. All results are returned as JSON-encoded TextContent.
"""

import asyncio
import json
import logging

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp import types

from .tools.read_file import read_file
from .tools.search_clause import search_clause
from .tools.save_report import save_report

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Server instantiation
# ---------------------------------------------------------------------------

# The server name is used by clients to identify this MCP server in logs and
# in multi-server setups. It must be stable across restarts.
server = Server("contract-agent")

# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------
# Each Tool definition is the schema that MCP clients use to understand what
# arguments a tool accepts. inputSchema follows JSON Schema (draft-07).

TOOLS: list[types.Tool] = [
    types.Tool(
        name="read_file",
        description=(
            "Read a contract file (PDF or TXT) from disk and return its "
            "full plain-text content, filename, and detected format."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute or relative path to the contract file.",
                },
            },
            "required": ["file_path"],
        },
    ),
    types.Tool(
        name="search_clause",
        description=(
            "Search for a keyword or clause type within contract text. "
            "Returns every matching line with surrounding context lines."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Full contract text to search within.",
                },
                "keyword": {
                    "type": "string",
                    "description": "Word or phrase to search for (case-insensitive).",
                },
                "context_lines": {
                    "type": "integer",
                    "description": "Lines of context above and below each match. Defaults to 3.",
                    "default": 3,
                },
            },
            "required": ["text", "keyword"],
        },
    ),
    types.Tool(
        name="save_report",
        description=(
            "Persist a finished contract analysis report to the reports/ "
            "directory. Returns the absolute file path and filename."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "contract_name": {
                    "type": "string",
                    "description": "Name of the source contract (used in the output filename).",
                },
                "report_content": {
                    "type": "string",
                    "description": "Full text content of the finished analysis report.",
                },
            },
            "required": ["contract_name", "report_content"],
        },
    ),
]


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    Return the catalogue of tools this server exposes.

    Called by MCP clients on startup and whenever they need to discover
    available capabilities. Returns the module-level TOOLS list so the
    registry is the single source of truth.
    """
    return TOOLS


@server.call_tool()
async def handle_call_tool(
    name: str,
    arguments: dict | None,
) -> list[types.TextContent]:
    """
    Route an incoming tool call to the correct implementation.

    Protocol:
        1. Extract typed arguments from the arguments dict.
        2. Call the pure-function tool from the tools/ subpackage.
        3. Serialise the result dict to a JSON string inside a TextContent block.

    Error handling:
        Expected errors (bad path, empty content, unsupported format, unknown
        tool name) are caught and returned as a TextContent error message.
        This keeps the MCP session alive — the calling agent receives
        structured feedback rather than an unhandled exception.

    Args:
        name:      The tool name as declared in TOOLS.
        arguments: Key/value pairs matching the tool's inputSchema.

    Returns:
        A single-element list containing a TextContent block with the
        JSON-encoded result (or an error message).
    """
    args = arguments or {}

    try:
        result = _dispatch(name, args)
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    except (KeyError, ValueError, FileNotFoundError, OSError) as exc:
        logger.exception("Tool '%s' raised an error.", name)
        error_payload = {"error": str(exc), "tool": name}
        return [types.TextContent(type="text", text=json.dumps(error_payload, indent=2))]


# ---------------------------------------------------------------------------
# Private dispatch
# ---------------------------------------------------------------------------


def _dispatch(name: str, args: dict) -> dict:
    """
    Map a tool name to its implementation and execute it.

    Separated from handle_call_tool so it can be unit-tested synchronously
    without spinning up an async event loop.

    Args:
        name: Tool name.
        args: Validated argument dict from the MCP request.

    Returns:
        A JSON-serialisable dict produced by the tool function.

    Raises:
        ValueError:        If the tool name is not recognised.
        (any tool errors): Propagated to handle_call_tool for logging.
    """
    if name == "read_file":
        return read_file(file_path=args["file_path"])

    if name == "search_clause":
        result = search_clause(
            text=args["text"],
            keyword=args["keyword"],
            context_lines=int(args.get("context_lines", 3)),
        )
        # ClauseMatch dataclasses must be converted to plain dicts for JSON.
        result["matches"] = [m.to_dict() for m in result["matches"]]
        return result

    if name == "save_report":
        return save_report(
            contract_name=args["contract_name"],
            report_content=args["report_content"],
        )

    raise ValueError(f"Unknown tool: '{name}'. Available tools: {[t.name for t in TOOLS]}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def _run() -> None:
    """Initialise and run the MCP server over stdio."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="contract-agent",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=types.ServerCapabilities(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(_run())
