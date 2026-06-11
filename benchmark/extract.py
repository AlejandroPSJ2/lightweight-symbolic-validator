"""Layer 2: structured extraction from raw LLM output."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field, ValidationError


class RiskOwnerLink(BaseModel):
    risk: str
    owner: str


class RiskControlLink(BaseModel):
    risk: str
    control: str


class RiskDependencyLink(BaseModel):
    risk: str
    dependency: str


class MitigationPlan(BaseModel):
    """Canonical mitigation plan schema."""

    risk_owners: list[RiskOwnerLink] = Field(default_factory=list)
    risk_controls: list[RiskControlLink] = Field(default_factory=list)
    risk_dependencies: list[RiskDependencyLink] = Field(default_factory=list)

    def to_mapping_dict(self) -> dict[str, list[dict[str, str]]]:
        return {
            "risk_owners": [row.model_dump() for row in self.risk_owners],
            "risk_controls": [row.model_dump() for row in self.risk_controls],
            "risk_dependencies": [row.model_dump() for row in self.risk_dependencies],
        }


class ExtractionResult(BaseModel):
    ok: bool
    plan: MitigationPlan | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def parse_raw_llm_output(raw: str | dict[str, Any]) -> dict[str, Any]:
    """Parse layer-1 output: strip markdown fences and load JSON object."""
    if isinstance(raw, dict):
        payload = raw
    else:
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        payload = json.loads(text)

    if not isinstance(payload, dict):
        raise ValueError("LLM response JSON must be an object")

    for key in ("risk_owners", "risk_controls", "risk_dependencies"):
        if key not in payload:
            raise ValueError(f"Missing key in LLM plan: {key}")
    return payload


def _map_row(
    row: Any,
    left_keys: tuple[str, ...],
    right_keys: tuple[str, ...],
    left: str,
    right: str,
) -> dict[str, str] | None:
    if not isinstance(row, dict):
        return None
    left_val = next((row[key] for key in left_keys if row.get(key) is not None), None)
    right_val = next((row[key] for key in right_keys if row.get(key) is not None), None)
    if left_val is None:
        return None
    return {left: str(left_val), right: str(right_val) if right_val is not None else ""}


def _expand_id_links(
    rows: list[Any],
    *,
    risk_keys: tuple[str, ...] = ("risk", "risk_id", "id"),
    plural_key: str,
    singular_keys: tuple[str, ...],
    left: str,
    right: str,
) -> list[dict[str, str]]:
    """Expand LLM rows with plural id lists (e.g. control_ids) into pairwise links."""
    links: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        risk_id = next((str(row[key]) for key in risk_keys if row.get(key) is not None), None)
        if risk_id is None:
            continue
        plural = row.get(plural_key)
        if isinstance(plural, list):
            for item in plural:
                if item is not None and str(item).strip():
                    links.append({left: risk_id, right: str(item)})
            continue
        mapped = _map_row(row, risk_keys, singular_keys, left, right)
        if mapped and mapped[right]:
            links.append(mapped)
    return links


def extract_plan(raw: str | dict[str, Any], case: dict[str, Any] | None = None) -> ExtractionResult:
    """
    Layer 2: normalize LLM key variants into MitigationPlan.

    Does not fix compliance — only structure and schema.
    """
    errors: list[str] = []
    warnings: list[str] = []

    try:
        payload = parse_raw_llm_output(raw)
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        return ExtractionResult(ok=False, errors=[str(exc)])

    risk_owners: list[dict[str, str]] = []
    for row in payload.get("risk_owners", []):
        mapped = _map_row(
            row,
            ("risk", "risk_id", "id"),
            ("owner", "owner_name"),
            "risk",
            "owner",
        )
        if mapped and mapped["owner"]:
            risk_owners.append(mapped)

    if not risk_owners:
        errors.append("risk_owners is empty after extraction")

    risk_controls = _expand_id_links(
        payload.get("risk_controls", []),
        plural_key="control_ids",
        singular_keys=("control", "control_id"),
        left="risk",
        right="control",
    )

    risk_dependencies = _expand_id_links(
        payload.get("risk_dependencies", []),
        plural_key="dependency_ids",
        singular_keys=("dependency", "dependency_id", "dep", "dep_id"),
        left="risk",
        right="dependency",
    )

    normalized = {
        "risk_owners": risk_owners,
        "risk_controls": risk_controls,
        "risk_dependencies": risk_dependencies,
    }

    try:
        plan = MitigationPlan.model_validate(normalized)
    except ValidationError as exc:
        errors.append(exc.errors()[0]["msg"] if exc.errors() else str(exc))
        return ExtractionResult(ok=False, errors=errors, warnings=warnings)

    if not plan.risk_owners:
        errors.append("risk_owners is empty after extraction")
    if not plan.risk_controls:
        errors.append("risk_controls is empty after extraction")
    if not plan.risk_dependencies:
        errors.append("risk_dependencies is empty after extraction")

    if errors:
        return ExtractionResult(ok=False, plan=plan, errors=errors, warnings=warnings)

    return ExtractionResult(ok=True, plan=plan, warnings=warnings)
