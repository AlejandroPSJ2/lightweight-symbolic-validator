"""Tests for set operations."""

import pytest

from discrete_structure_tool import run_tool


def test_difference_risks_without_control():
    output = run_tool(
        {
            "kind": "set",
            "operation": "difference",
            "a": ["R1", "R2", "R3"],
            "b": ["R1", "R3"],
        }
    )
    assert output["result"] == ["R2"]
    assert output["witness"]["missing_items"] == ["R2"]


def test_union():
    output = run_tool(
        {
            "kind": "set",
            "operation": "union",
            "a": ["a", "b"],
            "b": ["b", "c"],
        }
    )
    assert output["result"] == ["a", "b", "c"]


def test_intersection():
    output = run_tool(
        {
            "kind": "set",
            "operation": "intersection",
            "a": ["a", "b", "c"],
            "b": ["b", "c", "d"],
        }
    )
    assert output["result"] == ["b", "c"]


def test_symmetric_difference():
    output = run_tool(
        {
            "kind": "set",
            "operation": "symmetric_difference",
            "a": ["a", "b"],
            "b": ["b", "c"],
        }
    )
    assert set(output["result"]) == {"a", "c"}


def test_subset_true():
    output = run_tool(
        {
            "kind": "set",
            "operation": "subset",
            "a": ["a", "b"],
            "b": ["a", "b", "c"],
        }
    )
    assert output["result"] is True
    assert output["witness"] is None


def test_subset_false_with_witness():
    output = run_tool(
        {
            "kind": "set",
            "operation": "subset",
            "a": ["a", "d"],
            "b": ["a", "b", "c"],
        }
    )
    assert output["result"] is False
    assert output["witness"]["missing_items"] == ["d"]


def test_superset():
    output = run_tool(
        {
            "kind": "set",
            "operation": "superset",
            "a": ["a", "b", "c"],
            "b": ["a", "b"],
        }
    )
    assert output["result"] is True


def test_coverage():
    output = run_tool(
        {
            "kind": "set",
            "operation": "coverage",
            "a": ["C1", "C2"],
            "b": ["R1", "R2"],
        }
    )
    assert output["result"] is False
    assert set(output["witness"]["missing_items"]) == {"R1", "R2"}


def test_membership():
    output = run_tool(
        {
            "kind": "set",
            "operation": "membership",
            "a": ["x", "y"],
            "target": "x",
        }
    )
    assert output["result"] is True


def test_deduplicates_input_for_set_kind():
    output = run_tool(
        {
            "kind": "set",
            "operation": "union",
            "a": ["a", "a"],
            "b": ["a", "b"],
        }
    )
    assert output["result"] == ["a", "b"]
