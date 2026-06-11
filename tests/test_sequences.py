"""Tests for sequence operations."""

import pytest

from discrete_structure_tool import run_tool
from discrete_structure_tool.models import UnsupportedOperationError


def test_frequency_with_target():
    output = run_tool(
        {
            "kind": "sequence",
            "operation": "frequency",
            "a": ["s", "t", "r", "a", "w", "b", "e", "r", "r", "y"],
            "target": "r",
        }
    )
    assert output["result"] == 3
    assert output["witness"]["positions"] == [2, 7, 8]


def test_frequency_without_target():
    output = run_tool(
        {
            "kind": "sequence",
            "operation": "frequency",
            "a": ["a", "b", "a"],
        }
    )
    assert output["result"] == {"a": 2, "b": 1}
    assert output["witness"]["counts"] == {"a": 2, "b": 1}


def test_count_alias():
    output = run_tool(
        {
            "kind": "sequence",
            "operation": "count",
            "a": ["x", "y", "x"],
            "target": "x",
        }
    )
    assert output["result"] == 2
    assert output["witness"]["positions"] == [0, 2]


def test_positions():
    output = run_tool(
        {
            "kind": "sequence",
            "operation": "positions",
            "a": ["a", "b", "a"],
            "target": "a",
        }
    )
    assert output["result"] == [0, 2]


def test_membership():
    output = run_tool(
        {
            "kind": "sequence",
            "operation": "membership",
            "a": ["a", "b"],
            "target": "c",
        }
    )
    assert output["result"] is False
    assert output["witness"]["positions"] == []


def test_deduplicate_preserves_order():
    output = run_tool(
        {
            "kind": "sequence",
            "operation": "deduplicate",
            "a": ["b", "a", "b", "c", "a"],
        }
    )
    assert output["result"] == ["b", "a", "c"]
    assert set(output["witness"]["duplicate_items"]) == {"a", "b"}


def test_duplicates():
    output = run_tool(
        {
            "kind": "sequence",
            "operation": "duplicates",
            "a": ["a", "b", "a", "c", "b"],
        }
    )
    assert set(output["result"]) == {"a", "b"}
    assert output["witness"]["counts"]


def test_normalize_casefold_and_trim():
    output = run_tool(
        {
            "kind": "sequence",
            "operation": "frequency",
            "a": [" Hello ", "hello", "HELLO"],
            "target": "hello",
            "normalize": {"casefold": True, "trim": True, "nfkc": False},
        }
    )
    assert output["result"] == 3


def test_unsupported_operation():
    with pytest.raises(UnsupportedOperationError):
        run_tool({"kind": "sequence", "operation": "union", "a": ["a"]})


def test_missing_target_raises():
    with pytest.raises(ValueError, match="requires 'target'"):
        run_tool({"kind": "sequence", "operation": "count", "a": ["a"]})
