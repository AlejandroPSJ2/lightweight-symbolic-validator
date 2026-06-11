"""Build mitigation-plan validation reports from raw LLM output."""

from __future__ import annotations

from typing import Any

from benchmark.pipeline import pipeline_case_summary, run_pipeline
from benchmark.validate import rule_to_check_dict


def build_validation_report(
    case: dict[str, Any],
    raw_llm: str | dict[str, Any],
) -> dict[str, Any]:
    """
    Extract structures from LLM output, validate against case rules, return report dict.
    """
    raw = raw_llm if isinstance(raw_llm, dict) else _load_raw_json(raw_llm)
    pipeline_result = run_pipeline(case, raw)
    summary = pipeline_case_summary(pipeline_result)

    checks: list[dict[str, Any]] = []
    if pipeline_result.compliance is not None:
        checks = [rule_to_check_dict(rule) for rule in pipeline_result.compliance.rules]

    return {
        "case_id": case.get("id"),
        "architecture": "llm_output -> extract_plan -> validate_plan",
        "extraction_ok": summary["extraction_ok"],
        "extraction_errors": summary["extraction_errors"],
        "extraction_warnings": summary.get("extraction_warnings", []),
        "compliance_pct": summary["compliance_pct"],
        "all_passed": pipeline_result.all_passed,
        "failed_rules": summary.get("failed_rules", []),
        "failed_checks": summary.get("failed_checks", []),
        "checks": checks,
    }


def _load_raw_json(raw_llm: str) -> dict[str, Any]:
    import json

    from benchmark.extract import parse_raw_llm_output

    return parse_raw_llm_output(raw_llm)
