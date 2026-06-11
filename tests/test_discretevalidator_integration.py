"""Integration tests for DiscreteValidator MCP wrapper."""

from __future__ import annotations

import asyncio

import pytest

from discretevalidator import validate_discrete_structure
from discretevalidator.mcp_server import mcp


def test_validate_discrete_structure_sequence_frequency():
    output = validate_discrete_structure(
        {
            "kind": "sequence",
            "operation": "frequency",
            "a": list("strawberry"),
            "target": "r",
        }
    )
    assert output["result"] == 3
    assert output["witness"]["positions"] == [2, 7, 8]


def test_validate_discrete_structure_set_difference():
    output = validate_discrete_structure(
        {
            "kind": "set",
            "operation": "difference",
            "a": ["R1", "R2", "R3"],
            "b": ["R1", "R3"],
        }
    )
    assert output["result"] == ["R2"]
    assert output["witness"]["missing_items"] == ["R2"]


def test_validate_discrete_structure_rejects_invalid_payload():
    with pytest.raises(Exception):
        validate_discrete_structure({"kind": "sequence", "operation": "union", "a": ["a"]})


def test_mcp_server_registers_validate_discrete_structure():
    tools = asyncio.run(mcp.list_tools())
    names = {tool.name for tool in tools}
    assert "validate_discrete_structure" in names
