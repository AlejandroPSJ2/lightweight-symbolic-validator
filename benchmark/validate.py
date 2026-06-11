"""Validate mitigation plans against the six benchmark rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from discrete_structure_tool import run_tool


@dataclass
class RuleResult:
    rule_id: int
    name: str
    passed: bool
    detail: str | None = None
    witness: dict[str, Any] | None = None


@dataclass
class ComplianceReport:
    case_id: str
    rules: list[RuleResult] = field(default_factory=list)

    @property
    def passed_count(self) -> int:
        return sum(1 for rule in self.rules if rule.passed)

    @property
    def compliance_pct(self) -> float:
        if not self.rules:
            return 0.0
        return round(100.0 * self.passed_count / len(self.rules), 2)

    @property
    def all_passed(self) -> bool:
        return self.passed_count == len(self.rules)


def rule_to_check_dict(rule: RuleResult) -> dict[str, Any]:
    """Serialize a rule result for LLM feedback and benchmark reports."""
    payload: dict[str, Any] = {
        "check": rule.name,
        "rule_id": rule.rule_id,
        "passed": rule.passed,
    }
    if rule.detail:
        payload["detail"] = rule.detail
    if rule.witness:
        payload["witness"] = rule.witness
    return payload


def _enrich_owner_duplicate_witness(
    witness: dict[str, Any] | None,
    all_risk_ids: list[str],
) -> dict[str, Any] | None:
    if not witness:
        return None
    enriched = dict(witness)
    positions_by_key = enriched.get("positions")
    if isinstance(positions_by_key, dict):
        flat_positions = sorted({index for indices in positions_by_key.values() for index in indices})
        enriched["positions"] = flat_positions
        enriched["risk_ids"] = [
            all_risk_ids[index] for index in flat_positions if 0 <= index < len(all_risk_ids)
        ]
    return enriched


def _difference(missing_from: list[str], subtract: list[str]) -> list[str]:
    output = run_tool(
        {
            "kind": "set",
            "operation": "difference",
            "a": missing_from,
            "b": subtract,
        }
    )
    return output["result"]


def _coverage(covering: list[str], required: list[str]) -> tuple[bool, list[str]]:
    passed = run_tool(
        {
            "kind": "set",
            "operation": "coverage",
            "a": covering,
            "b": required,
        }
    )
    missing = _difference(required, covering)
    return bool(passed["result"]), missing


def validate_plan(
    case_id: str,
    risks: list[dict[str, Any]],
    controls: list[dict[str, Any]],
    dependencies: list[dict[str, Any]],
    risk_controls: list[dict[str, str]],
    risk_dependencies: list[dict[str, str]],
    risk_owners: list[dict[str, str]] | None = None,
) -> ComplianceReport:
    """Validate a proposed plan mapping against all six rules."""
    all_risk_ids = [risk["id"] for risk in risks]
    all_control_ids = [control["id"] for control in controls]
    all_dependency_ids = [dep["id"] for dep in dependencies]
    critical_ids = [risk["id"] for risk in risks if str(risk.get("severity", "")).upper() == "CRITICAL"]

    if risk_owners is None:
        risk_owners = [{"risk": risk["id"], "owner": risk.get("owner", "")} for risk in risks]

    owner_by_risk = {row["risk"]: row["owner"] for row in risk_owners}
    owners = [owner_by_risk.get(risk_id, "") for risk_id in all_risk_ids]
    risks_with_control = sorted({row["control"] for row in risk_controls})
    risks_with_control_from_risk_side = sorted({row["risk"] for row in risk_controls})
    mapped_controls = sorted({row["control"] for row in risk_controls})
    mapped_dependencies = sorted({row["dependency"] for row in risk_dependencies})
    risks_with_dependency = sorted({row["risk"] for row in risk_dependencies})
    critical_covered = sorted(
        {row["risk"] for row in risk_controls if row["risk"] in critical_ids}
    )

    duplicate_output = run_tool({"kind": "sequence", "operation": "duplicates", "a": owners})
    duplicate_owners = duplicate_output["result"]

    rules: list[RuleResult] = []

    passed, missing = _coverage(critical_covered, critical_ids)
    rules.append(
        RuleResult(
            rule_id=1,
            name="critical_has_control",
            passed=passed,
            detail=f"missing critical: {missing}" if missing else None,
            witness={"missing_items": missing} if missing else None,
        )
    )

    orphan_controls = _difference(all_control_ids, mapped_controls)
    rules.append(
        RuleResult(
            rule_id=2,
            name="no_orphan_controls",
            passed=len(orphan_controls) == 0,
            detail=f"orphan controls: {orphan_controls}" if orphan_controls else None,
            witness={"missing_items": orphan_controls} if orphan_controls else None,
        )
    )

    rules.append(
        RuleResult(
            rule_id=3,
            name="unique_owner_per_risk",
            passed=len(duplicate_owners) == 0,
            detail=f"duplicate owners: {duplicate_owners}" if duplicate_owners else None,
            witness=_enrich_owner_duplicate_witness(duplicate_output.get("witness"), all_risk_ids),
        )
    )

    passed, missing = _coverage(mapped_dependencies, all_dependency_ids)
    rules.append(
        RuleResult(
            rule_id=4,
            name="dependency_covered",
            passed=passed,
            detail=f"uncovered dependencies: {missing}" if missing else None,
            witness={"missing_items": missing} if missing else None,
        )
    )

    passed, missing = _coverage(risks_with_dependency, all_risk_ids)
    rules.append(
        RuleResult(
            rule_id=5,
            name="risk_has_dependency",
            passed=passed,
            detail=f"risks without dependency: {missing}" if missing else None,
            witness={"missing_items": missing} if missing else None,
        )
    )

    risks_without_owner = [
        risk_id
        for risk_id in all_risk_ids
        if not owner_by_risk.get(risk_id) or str(owner_by_risk.get(risk_id)).strip() == ""
    ]
    rules.append(
        RuleResult(
            rule_id=6,
            name="risk_has_owner",
            passed=len(risks_without_owner) == 0,
            detail=f"risks without owner: {risks_without_owner}" if risks_without_owner else None,
            witness={"missing_items": risks_without_owner} if risks_without_owner else None,
        )
    )

    del risks_with_control, risks_with_control_from_risk_side
    return ComplianceReport(case_id=case_id, rules=rules)


def aggregate_compliance(reports: list[ComplianceReport]) -> dict[str, Any]:
    """Summarize compliance across many cases."""
    if not reports:
        return {"cases": 0, "avg_compliance_pct": 0.0, "full_pass_rate_pct": 0.0}

    avg = round(sum(report.compliance_pct for report in reports) / len(reports), 2)
    full_pass = round(100.0 * sum(1 for report in reports if report.all_passed) / len(reports), 2)
    by_rule: dict[int, float] = {}
    for rule_id in range(1, 7):
        passed = sum(1 for report in reports for rule in report.rules if rule.rule_id == rule_id and rule.passed)
        by_rule[rule_id] = round(100.0 * passed / len(reports), 2)

    return {
        "cases": len(reports),
        "avg_compliance_pct": avg,
        "full_pass_rate_pct": full_pass,
        "by_rule_pct": by_rule,
    }
