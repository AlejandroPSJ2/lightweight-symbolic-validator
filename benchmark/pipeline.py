"""Three-layer pipeline: LLM output → extraction → validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from benchmark.extract import ExtractionResult, MitigationPlan, extract_plan
from benchmark.validate import ComplianceReport, rule_to_check_dict, validate_plan


@dataclass
class PipelineResult:
    case_id: str
    raw: dict[str, Any]
    extraction: ExtractionResult
    compliance: ComplianceReport | None = None

    @property
    def extraction_ok(self) -> bool:
        return self.extraction.ok

    @property
    def compliance_pct(self) -> float:
        if self.compliance is None:
            return 0.0
        return self.compliance.compliance_pct

    @property
    def all_passed(self) -> bool:
        return self.compliance is not None and self.compliance.all_passed


def validate_mitigation_plan(case: dict[str, Any], plan: MitigationPlan) -> ComplianceReport:
    """Layer 3: DiscreteStructureTool rule validation."""
    mapping = plan.to_mapping_dict()
    return validate_plan(
        case_id=case["id"],
        risks=case["risks"],
        controls=case["controls"],
        dependencies=case["dependencies"],
        risk_controls=mapping["risk_controls"],
        risk_dependencies=mapping["risk_dependencies"],
        risk_owners=mapping["risk_owners"],
    )


def run_pipeline(case: dict[str, Any], raw: dict[str, Any]) -> PipelineResult:
    """Run extraction then validation."""
    extraction = extract_plan(raw, case)
    if not extraction.ok or extraction.plan is None:
        return PipelineResult(case_id=case["id"], raw=raw, extraction=extraction)

    compliance = validate_mitigation_plan(case, extraction.plan)
    return PipelineResult(
        case_id=case["id"],
        raw=raw,
        extraction=extraction,
        compliance=compliance,
    )


def aggregate_pipeline_results(results: list[PipelineResult]) -> dict[str, Any]:
    if not results:
        return {
            "cases": 0,
            "extraction_success_rate_pct": 0.0,
            "avg_compliance_pct": 0.0,
            "full_pass_rate_pct": 0.0,
            "by_rule_pct": {},
        }

    extraction_ok = sum(1 for result in results if result.extraction_ok)
    avg_compliance = round(sum(result.compliance_pct for result in results) / len(results), 2)
    full_pass = round(100.0 * sum(1 for result in results if result.all_passed) / len(results), 2)

    by_rule: dict[int, float] = {}
    for rule_id in range(1, 7):
        passed = sum(
            1
            for result in results
            if result.compliance is not None
            for rule in result.compliance.rules
            if rule.rule_id == rule_id and rule.passed
        )
        by_rule[rule_id] = round(100.0 * passed / len(results), 2)

    return {
        "cases": len(results),
        "extraction_success_rate_pct": round(100.0 * extraction_ok / len(results), 2),
        "avg_compliance_pct": avg_compliance,
        "full_pass_rate_pct": full_pass,
        "by_rule_pct": by_rule,
    }


def pipeline_case_summary(result: PipelineResult) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "case_id": result.case_id,
        "extraction_ok": result.extraction_ok,
        "extraction_errors": result.extraction.errors,
        "extraction_warnings": result.extraction.warnings,
        "compliance_pct": result.compliance_pct,
        "failed_rules": [],
    }
    if result.compliance is not None:
        failed = [rule for rule in result.compliance.rules if not rule.passed]
        summary["failed_rules"] = [rule.rule_id for rule in failed]
        summary["failed_checks"] = [rule_to_check_dict(rule) for rule in failed]
    return summary
