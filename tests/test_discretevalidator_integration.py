"""Integration tests for DiscreteValidator MCP wrapper and migration demo."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path

import pytest

from discretevalidator import build_validation_report, validate_discrete_structure
from discretevalidator.mcp_server import mcp

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures"


def test_validate_discrete_structure_sequence_frequency():
    output = validate_discrete_structure(
        {
            "kind": "sequence",
            "operation": "frequency",
            "a": list("strawberry"),
            "target": "r",
        }
    )
    assert output["result"] == 3
    assert output["witness"]["positions"] == [2, 7, 8]


def test_validate_discrete_structure_set_difference():
    output = validate_discrete_structure(
        {
            "kind": "set",
            "operation": "difference",
            "a": ["R1", "R2", "R3"],
            "b": ["R1", "R3"],
        }
    )
    assert output["result"] == ["R2"]
    assert output["witness"]["missing_items"] == ["R2"]


def test_validate_discrete_structure_rejects_invalid_payload():
    with pytest.raises(Exception):
        validate_discrete_structure({"kind": "sequence", "operation": "union", "a": ["a"]})


def test_mcp_server_registers_validate_discrete_structure():
    tools = asyncio.run(mcp.list_tools())
    names = {tool.name for tool in tools}
    assert "validate_discrete_structure" in names


def test_build_validation_report_from_fixture():
    case = json.loads((FIXTURES / "case_var_001.json").read_text(encoding="utf-8"))
    raw = json.loads((FIXTURES / "llm_plan_var_001.json").read_text(encoding="utf-8"))
    report = build_validation_report(case, raw)
    assert report["case_id"] == "var_001"
    assert report["extraction_ok"] is True
    assert "checks" in report
    assert len(report["checks"]) == 6


def test_demo_migration_plan_script(tmp_path):
    out = tmp_path / "validation_report.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "demo_migration_plan.py"),
            "--response",
            str(FIXTURES / "llm_response_wrapper.json"),
            "--case",
            str(FIXTURES / "case_var_001.json"),
            "--output",
            str(out),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Extraction OK: True" in proc.stdout
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["case_id"] == "var_001"
    assert report["extraction_ok"] is True
    assert "compliance_pct" in report
