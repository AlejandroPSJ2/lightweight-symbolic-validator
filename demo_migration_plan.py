#!/usr/bin/env python
"""Demo: load LLM mitigation plan, extract structures, validate, write report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from discretevalidator.migration_report import build_validation_report

ROOT = Path(__file__).resolve().parent
DEFAULT_RESPONSE = ROOT / "benchmark" / "data" / "responses" / "no_tool" / "var_001.json"
DEFAULT_CASE = ROOT / "benchmark" / "data" / "variations.json"
DEFAULT_OUTPUT = ROOT / "validation_report.json"


def _load_case(case_path: Path, case_id: str | None) -> dict[str, Any]:
    data = json.loads(case_path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return data
    if case_id is None:
        return data[0]
    for case in data:
        if case["id"] == case_id:
            return case
    raise SystemExit(f"Case not found: {case_id}")


def _load_llm_raw(response_path: Path) -> dict[str, Any]:
    cached = json.loads(response_path.read_text(encoding="utf-8"))
    raw = cached.get("raw") or cached.get("plan")
    if raw is None:
        raise SystemExit(f"No raw/plan field in {response_path}")
    return raw


def run_demo(
    *,
    response_path: Path,
    case_path: Path,
    case_id: str | None,
    output_path: Path,
) -> dict[str, Any]:
    case = _load_case(case_path, case_id)
    raw = _load_llm_raw(response_path)
    report = build_validation_report(case, raw)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Mitigation plan validation demo")
    parser.add_argument(
        "--response",
        type=Path,
        default=DEFAULT_RESPONSE,
        help="Cached LLM response JSON (must contain raw or plan)",
    )
    parser.add_argument(
        "--case",
        type=Path,
        default=DEFAULT_CASE,
        help="variations.json or single-case JSON object",
    )
    parser.add_argument("--case-id", default=None, help="Case id inside variations.json")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output validation_report.json path",
    )
    args = parser.parse_args()

    report = run_demo(
        response_path=args.response,
        case_path=args.case,
        case_id=args.case_id,
        output_path=args.output,
    )

    print(f"Case: {report['case_id']}")
    print(f"Extraction OK: {report['extraction_ok']}")
    print(f"Compliance: {report['compliance_pct']}%")
    print(f"All passed: {report['all_passed']}")
    if report["failed_checks"]:
        print(f"Failed checks: {len(report['failed_checks'])}")
    print(f"Report: {args.output}")


if __name__ == "__main__":
    main()
