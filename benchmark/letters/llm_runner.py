"""LLM runner for letter-count benchmark cases."""

from __future__ import annotations

import json
import os
from typing import Any

from discrete_structure_tool import run_tool

from benchmark.llm_runner import LLMConfig, TOOL_SCHEMA, _client


def _letters_pre_inject_tool() -> bool:
    return os.getenv("BENCHMARK_LETTERS_PREINJECT", "0").strip().lower() in (
        "1",
        "true",
        "yes",
    )

def _execute_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "run_discrete_structure_tool":
        return run_tool(arguments)
    raise ValueError(f"Unknown tool: {name}")


def _tool_count(result: dict[str, Any]) -> int | None:
    value = result.get("result")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def solve_letter_with_llm(
    prompt: str,
    *,
    tool_enabled: bool,
    config: LLMConfig,
    case_input: dict[str, Any] | None = None,
) -> str:
    client = _client(config)
    system = (
        "Cuenta letras en palabras con precisión. "
        "Responde SOLO con un número entero (sin texto extra)."
    )
    if tool_enabled:
        system += (
            " Usa run_discrete_structure_tool (kind=sequence, operation=frequency) "
            "y responde con el valor de result."
        )
    else:
        system += " No uses herramientas ni código."

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]

    tools = [TOOL_SCHEMA] if tool_enabled else None
    tool_rounds = 0
    last_tool_count: int | None = None

    if tool_enabled and case_input and _letters_pre_inject_tool():
        tool_args = {
            "kind": "sequence",
            "operation": "frequency",
            "a": list(case_input["word"]),
            "target": case_input["target"],
        }
        tool_result = _execute_tool("run_discrete_structure_tool", tool_args)
        count = _tool_count(tool_result)
        if count is not None:
            last_tool_count = count
            messages.append(
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "letter_tool",
                            "type": "function",
                            "function": {
                                "name": "run_discrete_structure_tool",
                                "arguments": json.dumps(tool_args, ensure_ascii=False),
                            },
                        }
                    ],
                }
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": "letter_tool",
                    "content": json.dumps(tool_result, ensure_ascii=False),
                }
            )

    for _ in range(config.max_tool_rounds + 1):
        kwargs: dict[str, Any] = {
            "model": config.model,
            "messages": messages,
            "temperature": 0,
        }
        active_tools = tools if tool_enabled and tool_rounds < config.max_tool_rounds else None
        if active_tools:
            kwargs["tools"] = active_tools
            kwargs["tool_choice"] = "auto"

        response = client.chat.completions.create(**kwargs)
        message = response.choices[0].message

        if message.tool_calls and active_tools:
            tool_rounds += 1
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
                result = _execute_tool(call.function.name, args)
                count = _tool_count(result)
                if count is not None:
                    last_tool_count = count
                    return str(count)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )
            continue

        content = (message.content or "").strip()
        if content:
            return content
        if last_tool_count is not None:
            return str(last_tool_count)
        if tool_enabled:
            messages.append(
                {
                    "role": "user",
                    "content": "Responde ahora SOLO con el número entero final.",
                }
            )
            continue

    if last_tool_count is not None:
        return str(last_tool_count)

    raise RuntimeError("LLM did not return a letter count")
