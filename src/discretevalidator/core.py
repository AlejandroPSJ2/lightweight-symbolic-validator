"""Core validate_discrete_structure entry point (JSON API compatible with run_tool)."""

from __future__ import annotations

from typing import Any

from discrete_structure_tool import run_tool
from discrete_structure_tool.models import ToolInput


def validate_discrete_structure(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Run a deterministic discrete-structure operation.

    Accepts the same JSON payload as ``discrete_structure_tool.run_tool``:

    .. code-block:: json

        {
          "kind": "sequence | set | multiset | relation",
          "operation": "...",
          "a": [...],
          "b": [...],
          "target": "...",
          "keys": [...],
          "normalize": {"casefold": true, "trim": true, "nfkc": false}
        }

    Returns ``{"result": ..., "witness": {...}}``.
    """
    if not isinstance(payload, dict):
        raise TypeError("payload must be a JSON object")
    ToolInput.model_validate(payload)
    return run_tool(payload)
