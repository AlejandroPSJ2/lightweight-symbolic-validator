"""Evaluate letter-count LLM answers against ground truth."""

from __future__ import annotations

import json
import re
from typing import Any


def parse_count(raw: str) -> int | None:
    """Extract the first integer from an LLM response."""
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        value = json.loads(text)
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if isinstance(value, dict):
            for key in ("result", "count", "answer"):
                if key in value and isinstance(value[key], (int, float)):
                    return int(value[key])
    except (json.JSONDecodeError, TypeError, ValueError):
        pass

    match = re.search(r"-?\d+", text)
    return int(match.group()) if match else None


def evaluate_answer(case: dict[str, Any], raw: str) -> dict[str, Any]:
    parsed = parse_count(raw)
    expected = case["expected_count"]
    return {
        "case_id": case["id"],
        "expected": expected,
        "parsed": parsed,
        "correct": parsed == expected,
        "raw": raw,
    }


def aggregate_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    if not results:
        return {"cases": 0, "accuracy_pct": 0.0, "correct": 0}
    correct = sum(1 for item in results if item["correct"])
    total = len(results)
    return {
        "cases": total,
        "correct": correct,
        "accuracy_pct": round(100.0 * correct / total, 2),
    }
