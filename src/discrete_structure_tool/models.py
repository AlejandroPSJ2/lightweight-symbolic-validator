"""Pydantic models for tool input and output."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class NormalizeConfig(BaseModel):
    """String normalization options applied before operations."""

    casefold: bool = True
    trim: bool = True
    nfkc: bool = False


Kind = Literal["sequence", "set", "multiset", "relation"]

JsonValue = str | int | float | bool | None | list[Any] | dict[str, Any]


class ToolInput(BaseModel):
    """Validated input for a discrete-structure operation."""

    kind: Kind
    operation: str
    a: list[Any] = Field(default_factory=list)
    b: list[Any] | None = None
    target: Any | None = None
    keys: list[str] | None = None
    normalize: NormalizeConfig = Field(default_factory=NormalizeConfig)


class ToolOutput(BaseModel):
    """JSON-serializable operation result with optional witness evidence."""

    result: JsonValue
    witness: dict[str, JsonValue] | None = None


class UnsupportedOperationError(ValueError):
    """Raised when kind/operation combination is not supported."""

    def __init__(self, kind: str, operation: str) -> None:
        super().__init__(f"Unsupported operation '{operation}' for kind '{kind}'")
        self.kind = kind
        self.operation = operation
