"""MCP server exposing DiscreteStructureTool to Cursor and other MCP clients.

Deprecated: prefer ``discretevalidator.mcp_server`` and tool ``validate_discrete_structure``.
"""

from __future__ import annotations

from discretevalidator.mcp_server import main, mcp

__all__ = ["main", "mcp"]
