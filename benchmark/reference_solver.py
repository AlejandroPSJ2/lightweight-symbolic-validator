"""Reference solver used only for unit tests (not LLM benchmark runs)."""

from __future__ import annotations

from typing import Any

from discrete_structure_tool import run_tool

from benchmark.extract import extract_plan
from benchmark.pipeline import validate_mitigation_plan
from benchmark.validate import ComplianceReport, validate_plan


def _critical_ids(risks: list[dict[str, Any]]) -> list[str]:
    return [risk["id"] for risk in risks if str(risk.get("severity", "")).upper() == "CRITICAL"]


def build_reference_plan(case: dict[str, Any]) -> dict[str, Any]:
    """Build a compliant reference plan for validator tests."""
    risks = case["risks"]
    controls = case["controls"]
    dependencies = case["dependencies"]
    risk_ids = [risk["id"] for risk in risks]
    control_ids = [control["id"] for control in controls]
    dep_ids = [dep["id"] for dep in dependencies]

    owners = [risk.get("owner", "") for risk in risks]
    duplicate_output = run_tool({"kind": "sequence", "operation": "duplicates", "a": owners})
    duplicate_owners = set(duplicate_output["result"])

    spare_owners = [
        "Laura", "Tomás", "Beatriz", "Felipe", "Lucía", "Renata",
        "Camila", "Diego", "Pablo", "Sara", "Iván", "Noah", "Olivia", "Mateo",
    ]
    used_owners: set[str] = set()
    risk_owners: list[dict[str, str]] = []
    spare_index = 0

    for risk in risks:
        owner = str(risk.get("owner", "")).strip()
        if owner in duplicate_owners or owner in used_owners or not owner:
            while spare_index < len(spare_owners) and spare_owners[spare_index] in used_owners:
                spare_index += 1
            owner = spare_owners[spare_index] if spare_index < len(spare_owners) else f"Owner_{risk['id']}"
            spare_index += 1
        used_owners.add(owner)
        risk_owners.append({"risk": risk["id"], "owner": owner})

    critical = _critical_ids(risks)
    non_critical = [risk_id for risk_id in risk_ids if risk_id not in critical]

    risk_controls: list[dict[str, str]] = []
    control_index = 0

    for risk_id in critical:
        if control_index >= len(control_ids):
            break
        risk_controls.append({"risk": risk_id, "control": control_ids[control_index]})
        control_index += 1

    target_risks = non_critical + critical
    target_pointer = 0
    while control_index < len(control_ids):
        risk_id = target_risks[target_pointer % len(target_risks)]
        risk_controls.append({"risk": risk_id, "control": control_ids[control_index]})
        control_index += 1
        target_pointer += 1

    risk_dependencies: list[dict[str, str]] = []
    for index, dep_id in enumerate(dep_ids):
        risk_id = risk_ids[index % len(risk_ids)]
        risk_dependencies.append({"risk": risk_id, "dependency": dep_id})

    for index, risk_id in enumerate(risk_ids):
        if not any(row["risk"] == risk_id for row in risk_dependencies):
            dep_id = dep_ids[index % len(dep_ids)]
            risk_dependencies.append({"risk": risk_id, "dependency": dep_id})

    return {
        "risk_owners": risk_owners,
        "risk_controls": risk_controls,
        "risk_dependencies": risk_dependencies,
    }


def evaluate_case(case: dict[str, Any], plan: dict[str, Any]) -> ComplianceReport:
    extraction = extract_plan(plan, case)
    if extraction.ok and extraction.plan is not None:
        return validate_mitigation_plan(case, extraction.plan)
    return validate_plan(
        case_id=case["id"],
        risks=case["risks"],
        controls=case["controls"],
        dependencies=case["dependencies"],
        risk_controls=plan.get("risk_controls", []),
        risk_dependencies=plan.get("risk_dependencies", []),
        risk_owners=plan.get("risk_owners", []),
    )
