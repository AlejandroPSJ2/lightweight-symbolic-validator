"""Tests for validation witnesses and check serialization."""

from benchmark.llm_runner import _execute_tool
from benchmark.pipeline import pipeline_case_summary, run_pipeline
from benchmark.validate import rule_to_check_dict, validate_plan


def test_rule3_witness_includes_risk_ids_and_positions():
    risks = [
        {"id": "R1", "severity": "CRITICAL", "owner": "Ana"},
        {"id": "R8", "severity": "HIGH", "owner": "Ana"},
    ]
    report = validate_plan(
        case_id="example",
        risks=risks,
        controls=[{"id": "C1"}, {"id": "C2"}],
        dependencies=[{"id": "D1"}, {"id": "D2"}],
        risk_controls=[
            {"risk": "R1", "control": "C1"},
            {"risk": "R8", "control": "C2"},
        ],
        risk_dependencies=[
            {"risk": "R1", "dependency": "D1"},
            {"risk": "R8", "dependency": "D2"},
        ],
        risk_owners=[
            {"risk": "R1", "owner": "Ana"},
            {"risk": "R8", "owner": "Ana"},
        ],
    )
    rule3 = next(rule for rule in report.rules if rule.rule_id == 3)
    assert rule3.passed is False
    assert rule3.witness is not None
    assert rule3.witness["duplicate_items"] == ["Ana"]
    assert rule3.witness["positions"] == [0, 1]
    assert rule3.witness["risk_ids"] == ["R1", "R8"]


def test_coverage_rules_expose_missing_items_witness():
    report = validate_plan(
        case_id="coverage",
        risks=[{"id": "R1", "severity": "CRITICAL", "owner": "Ana"}],
        controls=[{"id": "C1"}],
        dependencies=[{"id": "D1"}],
        risk_controls=[],
        risk_dependencies=[],
        risk_owners=[{"risk": "R1", "owner": "Ana"}],
    )
    rule1 = next(rule for rule in report.rules if rule.rule_id == 1)
    assert rule1.witness == {"missing_items": ["R1"]}


def test_rule_to_check_dict_shape():
    report = validate_plan(
        case_id="example",
        risks=[
            {"id": "R1", "severity": "CRITICAL", "owner": "Ana"},
            {"id": "R8", "severity": "HIGH", "owner": "Ana"},
        ],
        controls=[{"id": "C1"}, {"id": "C2"}],
        dependencies=[{"id": "D1"}, {"id": "D2"}],
        risk_controls=[
            {"risk": "R1", "control": "C1"},
            {"risk": "R8", "control": "C2"},
        ],
        risk_dependencies=[
            {"risk": "R1", "dependency": "D1"},
            {"risk": "R8", "dependency": "D2"},
        ],
        risk_owners=[
            {"risk": "R1", "owner": "Ana"},
            {"risk": "R8", "owner": "Ana"},
        ],
    )
    rule3 = next(rule for rule in report.rules if rule.rule_id == 3)
    check = rule_to_check_dict(rule3)
    assert check["check"] == "unique_owner_per_risk"
    assert check["passed"] is False
    assert check["witness"]["risk_ids"] == ["R1", "R8"]


def test_execute_tool_validate_includes_witness():
    case = {
        "id": "case",
        "risks": [
            {"id": "R1", "severity": "CRITICAL", "owner": "Ana"},
            {"id": "R8", "severity": "HIGH", "owner": "Ana"},
        ],
        "controls": [{"id": "C1"}, {"id": "C2"}],
        "dependencies": [{"id": "D1"}, {"id": "D2"}],
    }
    payload = {
        "risk_owners": [
            {"risk": "R1", "owner": "Ana"},
            {"risk": "R8", "owner": "Ana"},
        ],
        "risk_controls": [
            {"risk": "R1", "control": "C1"},
            {"risk": "R8", "control": "C2"},
        ],
        "risk_dependencies": [
            {"risk": "R1", "dependency": "D1"},
            {"risk": "R8", "dependency": "D2"},
        ],
    }
    result = _execute_tool("validate_mitigation_plan", payload, case)
    assert result["ok"] is True
    assert len(result["failed_rules"]) == 1
    failed = result["failed_rules"][0]
    assert failed["check"] == "unique_owner_per_risk"
    assert failed["witness"]["risk_ids"] == ["R1", "R8"]


def test_pipeline_case_summary_includes_failed_checks():
    case = {
        "id": "case",
        "risks": [
            {"id": "R1", "severity": "CRITICAL", "owner": "Ana"},
            {"id": "R8", "severity": "HIGH", "owner": "Ana"},
        ],
        "controls": [{"id": "C1"}, {"id": "C2"}],
        "dependencies": [{"id": "D1"}, {"id": "D2"}],
    }
    raw = {
        "risk_owners": [
            {"risk": "R1", "owner": "Ana"},
            {"risk": "R8", "owner": "Ana"},
        ],
        "risk_controls": [
            {"risk": "R1", "control": "C1"},
            {"risk": "R8", "control": "C2"},
        ],
        "risk_dependencies": [
            {"risk": "R1", "dependency": "D1"},
            {"risk": "R8", "dependency": "D2"},
        ],
    }
    summary = pipeline_case_summary(run_pipeline(case, raw))
    assert summary["failed_rules"] == [3]
    assert summary["failed_checks"][0]["witness"]["duplicate_items"] == ["Ana"]
