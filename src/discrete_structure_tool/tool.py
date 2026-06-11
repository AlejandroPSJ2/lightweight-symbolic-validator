"""Public entry point for the discrete structure tool."""

from __future__ import annotations

from typing import Any

from discrete_structure_tool.models import ToolInput, ToolOutput
from discrete_structure_tool.operations import dispatch_operation


def run_tool(payload: dict[str, Any] | ToolInput) -> dict[str, Any]:
    """
    Execute a discrete-structure operation and return a JSON-serializable dict.

    Parameters
    ----------
    payload:
        Tool input as a dict or validated ToolInput model.

    Returns
    -------
    dict
        Serialized ToolOutput with ``result`` and optional ``witness``.
    """
    tool_input = payload if isinstance(payload, ToolInput) else ToolInput.model_validate(payload)

    result, witness = dispatch_operation(
        kind=tool_input.kind,
        operation=tool_input.operation,
        a=tool_input.a,
        b=tool_input.b,
        target=tool_input.target,
        keys=tool_input.keys,
        config=tool_input.normalize,
    )

    output = ToolOutput(result=result, witness=witness)
    return output.model_dump(mode="json")
