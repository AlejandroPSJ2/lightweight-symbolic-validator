"""Tests for the mitigation-plan benchmark loop."""

import json
from pathlib import Path

import pytest

from benchmark.generate import build_test_sets, generate_all, write_datasets
from benchmark.extract import parse_raw_llm_output
from benchmark.llm_runner import LLMConfigError
from benchmark.reference_solver import build_reference_plan
from benchmark.run_loop import run_loop
from benchmark.validate import validate_plan

BENCHMARK_DIR = Path(__file__).resolve().parents[1] / "benchmark"


@pytest.fixture(scope="module")
def variations():
    return generate_all(count=30, seed=42)


def test_generates_30_variations(variations):
    assert len(variations) == 30
    assert variations[0]["id"] == "var_001"


def test_two_prompt_sets_have_same_cases(variations):
    no_tool, with_tool = build_test_sets(variations)
    assert len(no_tool) == 30
    assert len(with_tool) == 30
    assert all(not item["tool_enabled"] for item in no_tool)
    assert all(item["tool_enabled"] for item in with_tool)
    assert no_tool[0]["case_id"] == with_tool[0]["case_id"]
    assert "NO uses DiscreteStructureTool" in no_tool[0]["prompt"]
    assert "DiscreteStructureTool" in with_tool[0]["prompt"]


def test_example_case_rule3_fails_before_fix():
    risks = [
        {"id": "R1", "severity": "CRITICAL", "owner": "Ana"},
        {"id": "R8", "severity": "HIGH", "owner": "Ana"},
    ]
    controls = [{"id": "C1"}, {"id": "C2"}]
    dependencies = [{"id": "D1"}, {"id": "D2"}]
    report = validate_plan(
        case_id="example",
        risks=risks,
        controls=controls,
        dependencies=dependencies,
        risk_controls=[
            {"risk": "R1", "control": "C1"},
            {"risk": "R8", "control": "C2"},
        ],
        risk_dependencies=[
            {"risk": "R1", "dependency": "D1"},
            {"risk": "R8", "dependency": "D2"},
        ],
    )
    rule3 = next(rule for rule in report.rules if rule.rule_id == 3)
    assert rule3.passed is False


def test_reference_plan_passes_all_variations(variations):
    for case in variations:
        plan = build_reference_plan(case)
        report = validate_plan(
            case_id=case["id"],
            risks=case["risks"],
            controls=case["controls"],
            dependencies=case["dependencies"],
            risk_controls=plan["risk_controls"],
            risk_dependencies=plan["risk_dependencies"],
            risk_owners=plan["risk_owners"],
        )
        assert report.all_passed, case["id"]


def test_extract_json_strips_markdown_fence():
    payload = parse_raw_llm_output(
        '```json\n{"risk_owners":[],"risk_controls":[],"risk_dependencies":[]}\n```'
    )
    assert payload == {"risk_owners": [], "risk_controls": [], "risk_dependencies": []}


def test_run_loop_reference_mode_reports_extraction(tmp_path):
    results = run_loop(data_dir=tmp_path, count=5, seed=7, mode="reference")
    assert results["mode"] == "reference"
    assert results["variations"] == 5
    assert results["architecture"] == "llm_output -> extract_plan -> validate_plan"
    assert (tmp_path / "results.json").exists()
    assert results["with_tool"]["extraction_success_rate_pct"] == 100.0
    assert results["with_tool"]["avg_compliance_pct"] == 100.0


def test_write_datasets_creates_files(tmp_path):
    write_datasets(tmp_path, count=30)
    assert (tmp_path / "variations.json").exists()
    assert (tmp_path / "set_no_tool.json").exists()
    assert (tmp_path / "set_with_tool.json").exists()
    no_tool = json.loads((tmp_path / "set_no_tool.json").read_text(encoding="utf-8"))
    assert len(no_tool) == 30


def test_llm_mode_requires_api_key(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("BENCHMARK_PROVIDER", raising=False)
    monkeypatch.setattr("benchmark.run_loop._load_dotenv", lambda: None)
    with pytest.raises(LLMConfigError):
        run_loop(data_dir=tmp_path, count=1, mode="llm", use_cache=False)
