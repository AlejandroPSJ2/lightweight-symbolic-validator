"""Tests for layer-2 plan extraction."""

from benchmark.extract import extract_plan, parse_raw_llm_output


def test_parse_raw_llm_output_strips_markdown_fence():
    payload = parse_raw_llm_output(
        '```json\n{"risk_owners":[],"risk_controls":[],"risk_dependencies":[]}\n```'
    )
    assert payload == {"risk_owners": [], "risk_controls": [], "risk_dependencies": []}


def test_extract_plan_maps_key_variants():
    raw = {
        "risk_owners": [{"risk_id": "R1", "owner": "Ana"}],
        "risk_controls": [{"risk_id": "R1", "control_id": "C1"}],
        "risk_dependencies": [{"risk_id": "R1", "dep_id": "D1"}],
    }
    result = extract_plan(raw)
    assert result.ok
    assert result.plan is not None
    assert result.plan.risk_owners[0].risk == "R1"
    assert result.plan.risk_controls[0].control == "C1"
    assert result.plan.risk_dependencies[0].dependency == "D1"


def test_extract_plan_expands_llm_plural_keys():
    raw = {
        "risk_owners": [{"risk_id": "R1", "owner_name": "Ana"}],
        "risk_controls": [{"risk_id": "R1", "control_ids": ["C1", "C2"]}],
        "risk_dependencies": [{"risk_id": "R1", "dependency_ids": ["D1", "D2"]}],
    }
    result = extract_plan(raw)
    assert result.ok
    assert result.plan is not None
    assert result.plan.risk_owners[0].owner == "Ana"
    assert [row.control for row in result.plan.risk_controls] == ["C1", "C2"]
    assert [row.dependency for row in result.plan.risk_dependencies] == ["D1", "D2"]


def test_extract_plan_fails_on_invalid_json():
    result = extract_plan("not json")
    assert not result.ok
    assert result.errors


def test_extract_plan_fails_when_risk_owners_missing():
    case = {
        "risks": [{"id": "R1", "owner": "Ana"}],
    }
    raw = {
        "risk_owners": [],
        "risk_controls": [{"risk": "R1", "control": "C1"}],
        "risk_dependencies": [{"risk": "R1", "dependency": "D1"}],
    }
    result = extract_plan(raw, case)
    assert not result.ok
    assert any("risk_owners" in error for error in result.errors)
