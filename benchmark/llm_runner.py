"""Call a real LLM for benchmark cases (with or without DiscreteStructureTool)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from discrete_structure_tool import run_tool

from benchmark.extract import extract_plan, parse_raw_llm_output
from benchmark.pipeline import validate_mitigation_plan
from benchmark.validate import rule_to_check_dict

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore[misc, assignment]


class LLMConfigError(RuntimeError):
    """Raised when LLM benchmark configuration is missing or invalid."""


@dataclass
class LLMConfig:
    api_key: str
    model: str = "gpt-4o-mini"
    base_url: str | None = None
    provider: str = "openai"
    max_tool_rounds: int = 6

    @classmethod
    def from_env(cls) -> LLMConfig:
        if OpenAI is None:
            raise LLMConfigError(
                'Install benchmark extras: pip install -e ".[benchmark]"'
            )

        provider = os.getenv("BENCHMARK_PROVIDER", "").strip().lower()
        gemini_key = os.getenv("GEMINI_API_KEY", "").strip() or os.getenv(
            "GOOGLE_API_KEY", ""
        ).strip()
        openai_key = os.getenv("OPENAI_API_KEY", "").strip()

        if not provider:
            provider = "gemini" if gemini_key and not openai_key else "openai"

        if provider == "gemini":
            if not gemini_key:
                raise LLMConfigError(
                    "GEMINI_API_KEY is required when BENCHMARK_PROVIDER=gemini. "
                    "Set it in discrete_structure_tool/.env (do not paste keys in chat)."
                )
            return cls(
                api_key=gemini_key,
                model=os.getenv("BENCHMARK_MODEL", "gemini-2.5-flash").strip(),
                base_url=os.getenv(
                    "OPENAI_BASE_URL",
                    "https://generativelanguage.googleapis.com/v1beta/openai/",
                ),
                provider="gemini",
                max_tool_rounds=int(os.getenv("BENCHMARK_MAX_TOOL_ROUNDS", "6")),
            )

        if not openai_key:
            raise LLMConfigError(
                "OPENAI_API_KEY is required for LLM benchmark runs (or set "
                "BENCHMARK_PROVIDER=gemini with GEMINI_API_KEY). "
                "Use discrete_structure_tool/.env"
            )
        return cls(
            api_key=openai_key,
            model=os.getenv("BENCHMARK_MODEL", "gpt-4o-mini").strip(),
            base_url=os.getenv("OPENAI_BASE_URL") or None,
            provider="openai",
            max_tool_rounds=int(os.getenv("BENCHMARK_MAX_TOOL_ROUNDS", "6")),
        )


def _max_repair_rounds() -> int:
    return int(os.getenv("BENCHMARK_MAX_REPAIR_ROUNDS", "1"))


TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "run_discrete_structure_tool",
        "description": (
            "Exact symbolic checks. Use operations: frequency, duplicates, difference, "
            "coverage, union, intersection, subset, membership, project, group_by, join."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "kind": {
                    "type": "string",
                    "enum": ["sequence", "set", "multiset", "relation"],
                },
                "operation": {"type": "string"},
                "a": {"type": "array"},
                "b": {"type": "array"},
                "target": {},
                "keys": {"type": "array", "items": {"type": "string"}},
                "normalize": {
                    "type": "object",
                    "properties": {
                        "casefold": {"type": "boolean"},
                        "trim": {"type": "boolean"},
                        "nfkc": {"type": "boolean"},
                    },
                },
            },
            "required": ["kind", "operation", "a"],
        },
    },
}

VALIDATE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "validate_mitigation_plan",
        "description": "Validate a mitigation plan against the 6 benchmark rules.",
        "parameters": {
            "type": "object",
            "properties": {
                "risk_owners": {"type": "array"},
                "risk_controls": {"type": "array"},
                "risk_dependencies": {"type": "array"},
            },
            "required": ["risk_owners", "risk_controls", "risk_dependencies"],
        },
    },
}


def _client(config: LLMConfig) -> Any:
    kwargs: dict[str, Any] = {"api_key": config.api_key}
    if config.base_url:
        kwargs["base_url"] = config.base_url
    return OpenAI(**kwargs)


def _parse_llm_response(content: str) -> dict[str, Any]:
    return parse_raw_llm_output(content)


def _repair_message(*, failed_checks: list[dict[str, Any]] | None = None, extraction_errors: list[str] | None = None) -> str:
    payload: dict[str, Any] = {
        "instruction": (
            "Fix the plan using only failed_checks.witness (or extraction_errors). "
            "Do not invent IDs. Re-call validate_mitigation_plan before the final JSON."
        ),
    }
    if failed_checks:
        payload["failed_checks"] = failed_checks
    if extraction_errors:
        payload["extraction_errors"] = extraction_errors
    return json.dumps(payload, ensure_ascii=False)


def _validate_plan_payload(payload: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    extraction = extract_plan(payload, case)
    if not extraction.ok or extraction.plan is None:
        return {
            "ok": False,
            "extraction_errors": extraction.errors,
            "compliance_pct": 0.0,
            "all_passed": False,
            "failed_rules": [],
        }
    report = validate_mitigation_plan(case, extraction.plan)
    return {
        "ok": True,
        "compliance_pct": report.compliance_pct,
        "all_passed": report.all_passed,
        "failed_rules": [
            rule_to_check_dict(rule)
            for rule in report.rules
            if not rule.passed
        ],
    }


def _execute_tool(name: str, arguments: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    try:
        if name == "run_discrete_structure_tool":
            return run_tool(arguments)
        if name == "validate_mitigation_plan":
            extraction = extract_plan(arguments, case)
            if not extraction.ok or extraction.plan is None:
                return {
                    "ok": False,
                    "extraction_errors": extraction.errors,
                    "compliance_pct": 0.0,
                    "all_passed": False,
                    "failed_rules": [],
                }
            report = validate_mitigation_plan(case, extraction.plan)
            return {
                "ok": True,
                "compliance_pct": report.compliance_pct,
                "all_passed": report.all_passed,
                "failed_rules": [
                    rule_to_check_dict(rule)
                    for rule in report.rules
                    if not rule.passed
                ],
            }
        raise ValueError(f"Unknown tool: {name}")
    except Exception as exc:
        return {"error": str(exc), "ok": False}


def solve_with_llm(
    prompt: str,
    case: dict[str, Any],
    *,
    tool_enabled: bool,
    config: LLMConfig | None = None,
) -> dict[str, Any]:
    """Run one benchmark case against a real LLM. Returns layer-1 raw JSON."""
    config = config or LLMConfig.from_env()
    client = _client(config)

    system = (
        "Eres un planificador de mitigación. Devuelve SOLO JSON válido con las claves "
        "risk_owners, risk_controls, risk_dependencies. "
        "No incluyas markdown ni texto extra en la respuesta final."
    )
    if tool_enabled:
        system += (
            " Tienes herramientas run_discrete_structure_tool y validate_mitigation_plan. "
            "Incluye siempre risk_owners, risk_controls y risk_dependencies en el JSON final. "
            "Si validate_mitigation_plan devuelve failed_checks, corrige usando solo witness "
            "y valida de nuevo antes de entregar."
        )
    else:
        system += " No uses herramientas externas ni código."

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    tools = [TOOL_SCHEMA, VALIDATE_SCHEMA] if tool_enabled else None
    repair_rounds = 0

    for _ in range(config.max_tool_rounds + 1):
        kwargs: dict[str, Any] = {
            "model": config.model,
            "messages": messages,
            "temperature": 0,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = client.chat.completions.create(**kwargs)
        message = response.choices[0].message

        if message.tool_calls:
            messages.append(
                {
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {
                                "name": call.function.name,
                                "arguments": call.function.arguments,
                            },
                        }
                        for call in message.tool_calls
                    ],
                }
            )
            for call in message.tool_calls:
                args = json.loads(call.function.arguments or "{}")
                result = _execute_tool(call.function.name, args, case)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )
                if (
                    call.function.name == "validate_mitigation_plan"
                    and result.get("ok")
                    and not result.get("all_passed")
                    and repair_rounds < _max_repair_rounds()
                ):
                    repair_rounds += 1
                    messages.append(
                        {
                            "role": "user",
                            "content": _repair_message(
                                failed_checks=result.get("failed_rules", [])
                            ),
                        }
                    )
                elif (
                    call.function.name == "validate_mitigation_plan"
                    and not result.get("ok")
                    and repair_rounds < _max_repair_rounds()
                ):
                    repair_rounds += 1
                    messages.append(
                        {
                            "role": "user",
                            "content": _repair_message(
                                extraction_errors=result.get("extraction_errors", [])
                            ),
                        }
                    )
            continue

        content = message.content or ""
        if not content.strip() and tool_enabled:
            messages.append(
                {
                    "role": "user",
                    "content": "Entrega ahora el JSON final del plan (risk_owners, risk_controls, risk_dependencies).",
                }
            )
            continue

        if tool_enabled and content.strip():
            try:
                payload = _parse_llm_response(content)
            except (json.JSONDecodeError, ValueError, TypeError):
                if repair_rounds < _max_repair_rounds():
                    repair_rounds += 1
                    messages.append({"role": "assistant", "content": content})
                    messages.append(
                        {
                            "role": "user",
                            "content": _repair_message(
                                extraction_errors=["Invalid JSON in final response"]
                            ),
                        }
                    )
                    continue
                payload = {"risk_owners": [], "risk_controls": [], "risk_dependencies": []}

            validation = _validate_plan_payload(payload, case)
            if validation.get("all_passed"):
                return payload
            if repair_rounds < _max_repair_rounds():
                repair_rounds += 1
                messages.append({"role": "assistant", "content": content})
                if not validation.get("ok"):
                    messages.append(
                        {
                            "role": "user",
                            "content": _repair_message(
                                extraction_errors=validation.get("extraction_errors", [])
                            ),
                        }
                    )
                else:
                    messages.append(
                        {
                            "role": "user",
                            "content": _repair_message(
                                failed_checks=validation.get("failed_rules", [])
                            ),
                        }
                    )
                continue
            return payload

        try:
            return _parse_llm_response(content)
        except (json.JSONDecodeError, ValueError, TypeError):
            messages.append({"role": "assistant", "content": content})
            messages.append(
                {
                    "role": "user",
                    "content": "JSON inválido. Devuelve SOLO JSON válido con risk_owners, risk_controls, risk_dependencies.",
                }
            )
            continue

    raise RuntimeError(f"LLM exceeded max tool rounds for case {case['id']}")
