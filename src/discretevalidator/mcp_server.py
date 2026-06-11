"""DiscreteValidator MCP server (FastMCP)."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from discretevalidator.core import validate_discrete_structure

mcp = FastMCP(
    "Lightweight Symbolic Validator (PoC)",
    instructions=(
        "Local PoC MCP mockup. Call validate_discrete_structure with a JSON payload "
        "(kind, operation, a, ...) for exact letter counts, set logic, deduplication, "
        "and relation operations. Cite witness fields in your answer."
    ),
)


@mcp.tool(name="validate_discrete_structure")
def validate_discrete_structure_tool(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Validate or compute discrete structures (sequences, sets, multisets, relations).

    ``payload`` must follow the DiscreteStructureTool JSON API, for example:

    - Count letters: ``{"kind": "sequence", "operation": "frequency", "a": ["s","t","r",...], "target": "r"}``
    - Set difference: ``{"kind": "set", "operation": "difference", "a": [...], "b": [...]}``
    - Relation project: ``{"kind": "relation", "operation": "project", "a": [{...}], "keys": ["risk"]}``

    Returns ``{"result": <value>, "witness": {...}}``.
    """
    return validate_discrete_structure(payload)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
