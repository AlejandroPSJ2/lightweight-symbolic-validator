"""Tests for multiset operations."""

from discrete_structure_tool import run_tool


def test_multiset_frequency():
    output = run_tool(
        {
            "kind": "multiset",
            "operation": "frequency",
            "a": ["a", "a", "b"],
            "target": "a",
        }
    )
    assert output["result"] == 2
    assert output["witness"]["positions"] == [0, 1]


def test_multiset_union():
    output = run_tool(
        {
            "kind": "multiset",
            "operation": "union",
            "a": ["a", "a"],
            "b": ["a", "b"],
        }
    )
    assert output["result"] == ["a", "a", "a", "b"]
    assert output["witness"]["counts"]["a"] == 3


def test_multiset_intersection():
    output = run_tool(
        {
            "kind": "multiset",
            "operation": "intersection",
            "a": ["a", "a", "b"],
            "b": ["a", "b", "b"],
        }
    )
    assert output["result"] == ["a", "b"]


def test_multiset_difference():
    output = run_tool(
        {
            "kind": "multiset",
            "operation": "difference",
            "a": ["a", "a", "b"],
            "b": ["a"],
        }
    )
    assert output["result"] == ["a", "b"]


def test_multiset_subset():
    output = run_tool(
        {
            "kind": "multiset",
            "operation": "subset",
            "a": ["a", "b"],
            "b": ["a", "a", "b", "c"],
        }
    )
    assert output["result"] is True


def test_multiset_subset_false():
    output = run_tool(
        {
            "kind": "multiset",
            "operation": "subset",
            "a": ["a", "a"],
            "b": ["a"],
        }
    )
    assert output["result"] is False
    assert output["witness"]["counts"]["a"] == 1


def test_multiset_duplicates():
    output = run_tool(
        {
            "kind": "multiset",
            "operation": "duplicates",
            "a": ["x", "x", "y"],
        }
    )
    assert output["result"] == ["x"]
    assert output["witness"]["counts"]["x"] == 2
