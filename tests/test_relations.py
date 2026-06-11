"""Tests for relation operations."""

import pytest

from discrete_structure_tool import run_tool


def test_project():
    output = run_tool(
        {
            "kind": "relation",
            "operation": "project",
            "a": [
                {"risk": "R1", "control": "C1", "owner": "Ana"},
                {"risk": "R2", "control": None, "owner": "Luis"},
            ],
            "keys": ["risk", "control"],
        }
    )
    assert output["result"] == [
        {"risk": "R1", "control": "C1"},
        {"risk": "R2", "control": None},
    ]
    assert output["witness"] is None


def test_group_by_count():
    output = run_tool(
        {
            "kind": "relation",
            "operation": "group_by",
            "a": [
                {"dept": "IT", "role": "dev"},
                {"dept": "IT", "role": "dev"},
                {"dept": "HR", "role": "recruiter"},
            ],
            "keys": ["dept"],
        }
    )
    assert output["result"] == [
        {"dept": "HR", "count": 1},
        {"dept": "IT", "count": 2},
    ]


def test_join():
    output = run_tool(
        {
            "kind": "relation",
            "operation": "join",
            "a": [{"id": 1, "name": "Ana"}],
            "b": [{"id": 1, "city": "Madrid"}],
            "keys": ["id"],
        }
    )
    assert output["result"] == [{"id": 1, "name": "Ana", "city_b": "Madrid"}]


def test_join_unmatched_witness():
    output = run_tool(
        {
            "kind": "relation",
            "operation": "join",
            "a": [{"id": 1}, {"id": 2}],
            "b": [{"id": 1, "x": 1}],
            "keys": ["id"],
        }
    )
    assert len(output["result"]) == 1
    assert output["witness"]["missing_items"] == [{"id": 2}]


def test_duplicates_by_keys():
    output = run_tool(
        {
            "kind": "relation",
            "operation": "duplicates",
            "a": [
                {"risk": "R1", "control": "C1"},
                {"risk": "R1", "control": "C1"},
                {"risk": "R2", "control": None},
            ],
            "keys": ["risk", "control"],
        }
    )
    assert len(output["result"]) == 1
    assert output["witness"]["counts"]


def test_coverage_within_relation():
    output = run_tool(
        {
            "kind": "relation",
            "operation": "coverage",
            "a": [
                {"risk": "R1", "control": "C1"},
                {"risk": "R2", "control": None},
            ],
            "keys": ["risk", "control"],
        }
    )
    assert output["result"] is False
    assert "R2" in output["witness"]["missing_items"]


def test_membership_row():
    output = run_tool(
        {
            "kind": "relation",
            "operation": "membership",
            "a": [{"risk": "R1"}, {"risk": "R2"}],
            "target": {"risk": "R2"},
            "keys": ["risk"],
        }
    )
    assert output["result"] is True
    assert output["witness"]["positions"] == [1]


def test_invalid_row_type():
    with pytest.raises(ValueError, match="must be dicts"):
        run_tool({"kind": "relation", "operation": "project", "a": ["not-a-dict"], "keys": ["x"]})
