"""Tests for the 3-layer benchmark pipeline."""

from benchmark.extract import extract_plan
from benchmark.generate import generate_all
from benchmark.pipeline import aggregate_pipeline_results, run_pipeline
from benchmark.reference_solver import build_reference_plan


def test_run_pipeline_reference_plan_passes():
    case = generate_all(count=1, seed=1)[0]
    raw = build_reference_plan(case)
    result = run_pipeline(case, raw)
    assert result.extraction_ok
    assert result.compliance is not None
    assert result.all_passed


def test_run_pipeline_failed_extraction_skips_compliance():
    case = generate_all(count=1, seed=1)[0]
    result = run_pipeline(case, "invalid")
    assert not result.extraction_ok
    assert result.compliance is None
    assert result.compliance_pct == 0.0


def test_aggregate_pipeline_results_includes_extraction_rate():
    case = generate_all(count=1, seed=1)[0]
    good = run_pipeline(case, build_reference_plan(case))
    bad = run_pipeline(case, "invalid")
    summary = aggregate_pipeline_results([good, bad])
    assert summary["cases"] == 2
    assert summary["extraction_success_rate_pct"] == 50.0
    assert summary["full_pass_rate_pct"] == 50.0


def test_extract_then_validate_matches_direct_reference():
    case = generate_all(count=1, seed=3)[0]
    raw = build_reference_plan(case)
    pipeline_result = run_pipeline(case, raw)
    extraction = extract_plan(raw, case)
    assert pipeline_result.extraction_ok == extraction.ok
    assert pipeline_result.all_passed
