# DiscreteValidator

**DiscreteValidator** is the MCP-facing name for DiscreteStructureTool (see below): a FastMCP server that exposes deterministic symbolic checks to LLM agents via the tool `validate_discrete_structure`. The JSON payload is identical to `run_tool`.

## Installation

```bash
cd discrete_structure_tool
pip install -e ".[mcp,dev]"
```

## Quick start (Python)

```python
from discretevalidator import validate_discrete_structure

output = validate_discrete_structure({
    "kind": "sequence",
    "operation": "frequency",
    "a": list("strawberry"),
    "target": "r",
})
# {'result': 3, 'witness': {'positions': [2, 7, 8], 'counts': {'r': 3}}}
```

## Mitigation plan demo

Load a cached LLM response, extract structures, validate rules, write `validation_report.json`:

```bash
python demo_migration_plan.py \
  --response tests/fixtures/llm_response_wrapper.json \
  --case tests/fixtures/case_var_001.json \
  --output validation_report.json
```

---

# DiscreteStructureTool

Deterministic Python library for lightweight symbolic reasoning over **sequences**, **sets**, **multisets**, and **relations**. Designed to give LLMs exact counts, positions, and set logic instead of approximate mental arithmetic.

## Installation

```bash
cd discrete_structure_tool
pip install -e ".[dev]"
```

## Quick start

```python
from discrete_structure_tool import run_tool

output = run_tool({
    "kind": "sequence",
    "operation": "frequency",
    "a": ["s", "t", "r", "a", "w", "b", "e", "r", "r", "y"],
    "target": "r",
})
print(output)
# {'result': 3, 'witness': {'positions': [2, 7, 8], 'counts': {'r': 3}}}
```

Every call returns JSON-serializable output:

```json
{
  "result": <value>,
  "witness": { "...": "optional evidence" }
}
```

## API

```python
run_tool({
    "kind": "sequence | set | multiset | relation",
    "operation": "...",
    "a": [...],
    "b": [...],           # optional, required for binary ops
    "target": ...,         # optional, required for lookup ops
    "keys": [...],         # optional, required for relation ops
    "normalize": {
        "casefold": true,
        "trim": true,
        "nfkc": false
    }
})
```

### Supported operations

| Kind | Operations |
|------|------------|
| **sequence** | `frequency`, `count`, `positions`, `membership`, `deduplicate`, `duplicates` |
| **set** | `union`, `intersection`, `difference`, `symmetric_difference`, `subset`, `superset`, `membership`, `coverage`, `duplicates` |
| **multiset** | `frequency`, `union`, `intersection`, `difference`, `subset`, `superset`, `membership`, `duplicates` |
| **relation** | `project`, `group_by`, `join`, `duplicates`, `coverage`, `membership` |

### Examples

**Count letters with positions**

```python
run_tool({
    "kind": "sequence",
    "operation": "frequency",
    "a": ["s","t","r","a","w","b","e","r","r","y"],
    "target": "r",
})
# result: 3, witness.positions: [2, 7, 8]
```

**Risks without control (set difference)**

```python
run_tool({
    "kind": "set",
    "operation": "difference",
    "a": ["R1", "R2", "R3"],
    "b": ["R1", "R3"],
})
# result: ["R2"], witness.missing_items: ["R2"]
```

**Project relation columns**

```python
run_tool({
    "kind": "relation",
    "operation": "project",
    "a": [
        {"risk": "R1", "control": "C1", "owner": "Ana"},
        {"risk": "R2", "control": None, "owner": "Luis"},
    ],
    "keys": ["risk", "control"],
})
```

**Group by and count**

```python
run_tool({
    "kind": "relation",
    "operation": "group_by",
    "a": [
        {"team": "A", "status": "open"},
        {"team": "A", "status": "open"},
        {"team": "B", "status": "closed"},
    ],
    "keys": ["team"],
})
# result: [{"team": "A", "count": 2}, {"team": "B", "count": 1}]
```

## Witness fields

Operations may attach evidence to help an LLM explain its answer:

| Field | Meaning |
|-------|---------|
| `positions` | Zero-based indices where a target appears |
| `counts` | Frequency map |
| `missing_items` | Items not covered / in a difference |
| `duplicate_items` | Repeated values or rows |

## Normalization

Strings are normalized for **matching only**; results preserve the original input values.

- `trim`: strip whitespace before comparison
- `casefold`: case-insensitive matching
- `nfkc`: Unicode NFKC normalization before comparison

Disable normalization when exact casing matters:

```python
"normalize": {"casefold": False, "trim": False, "nfkc": False}
```

## Using with LLMs (function calling / MCP)

LLMs often miscount characters, confuse set logic, or hallucinate join results. **DiscreteValidator** (via `validate_discrete_structure`) offloads those steps to deterministic code and returns verifiable witnesses.

### MCP server (DiscreteValidator / FastMCP)

Run locally:

```bash
pip install -e ".[mcp]"
python -m discretevalidator.mcp_server
# or: discretevalidator-mcp
```

**Claude Desktop** — add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "discretevalidator": {
      "command": "python",
      "args": ["-m", "discretevalidator.mcp_server"],
      "cwd": "C:/path/to/set_tool/discrete_structure_tool"
    }
  }
}
```

**Cursor** — this repo ships `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "discretevalidator": {
      "command": "python",
      "args": ["-m", "discretevalidator.mcp_server"]
    }
  }
}
```

Enable **discretevalidator** under **Settings → Tools & MCP**, then reload the window.

**OpenAI function calling** — register one tool (handler calls the same JSON API):

```json
{
  "type": "function",
  "function": {
    "name": "validate_discrete_structure",
    "description": "Deterministic symbolic operations on sequences, sets, multisets, and relations.",
    "parameters": {
      "type": "object",
      "properties": {
        "payload": {
          "type": "object",
          "description": "DiscreteStructureTool request",
          "properties": {
            "kind": {"type": "string", "enum": ["sequence", "set", "multiset", "relation"]},
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
                "nfkc": {"type": "boolean"}
              }
            }
          },
          "required": ["kind", "operation", "a"]
        }
      },
      "required": ["payload"]
    }
  }
}
```

Handler:

```python
from discretevalidator import validate_discrete_structure

def handle_tool_call(name: str, arguments: dict) -> dict:
    if name == "validate_discrete_structure":
        return validate_discrete_structure(arguments["payload"])
    raise ValueError(f"Unknown tool: {name}")
```

Example call:

```python
validate_discrete_structure({
    "kind": "sequence",
    "operation": "frequency",
    "a": list("strawberry"),
    "target": "r",
})
```

**Prompting tip:** instruct the model to call `validate_discrete_structure` whenever it needs exact counts, set differences, deduplication, or relational joins—then cite `witness` fields in its explanation.

### Legacy library import

You can still call the core library directly:

```python
from discrete_structure_tool import run_tool

def handle_tool_call(arguments: dict) -> dict:
    return run_tool(arguments)
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## Cursor integration (MCP)

1. Install with MCP support:

```bash
pip install -e "./discrete_structure_tool[mcp]"
```

2. Open this folder (`set_tool`) in Cursor.
3. Enable the **discretevalidator** MCP server under **Settings → Tools & MCP**.
4. Reload the window if the server does not appear.

The agent rule in `.cursor/rules/discrete-structure-tool.mdc` instructs the assistant to use `validate_discrete_structure` for counts, set logic, and relation operations instead of guessing.

Manual MCP run (debug):

```bash
python -m discretevalidator.mcp_server
```

Legacy alias (same server):

```bash
python -m discrete_structure_tool.mcp_server
```

## Benchmark (30 variaciones, LLM real)

Ambos sets llaman al **mismo LLM**. La diferencia es el prompt y las tools:

| Set | Prompt | Tools |
|-----|--------|-------|
| `set_no_tool` | sin herramienta | ninguna |
| `set_with_tool` | con DiscreteStructureTool | `run_discrete_structure_tool` + `validate_mitigation_plan` |

### Pipeline (3 capas)

```
LLM output  →  extract_plan (extract.py)  →  validate_plan (validate.py / DiscreteStructureTool)
   capa 1              capa 2                              capa 3
```

- **Capa 1:** respuesta cruda del LLM (JSON o tool calls).
- **Capa 2:** `extract.py` normaliza variantes de claves (`risk_id` → `risk`, etc.) y valida el esquema `MitigationPlan`. Métrica: `extraction_success_rate_pct`.
- **Capa 3:** `pipeline.py` → `validate_plan()` aplica las 6 reglas con DiscreteStructureTool. Métricas: `avg_compliance_pct`, `full_pass_rate_pct`.
- Cada regla fallida incluye un **witness** accionable (`missing_items`, `duplicate_items`, `risk_ids`, `positions`) expuesto al LLM vía `validate_mitigation_plan` y en `results.json` (`failed_checks`).

`run_loop.py` ejecuta el pipeline completo y escribe `benchmark/data/results.json` con métricas de extracción y cumplimiento por set.

### Setup

```bash
pip install -e ".[benchmark]"
copy .env.example .env   # Windows
# Edita .env → OPENAI_API_KEY=sk-...
```

Variables:

| Variable | Requerida | Default |
|----------|-----------|---------|
| `GEMINI_API_KEY` | sí (Gemini) | — |
| `BENCHMARK_PROVIDER` | no | `gemini` si hay GEMINI key, si no `openai` |
| `BENCHMARK_MODEL` | no | `gemini-2.5-flash` / `gpt-4o-mini` |
| `OPENAI_API_KEY` | sí (OpenAI) | — |
| `OPENAI_BASE_URL` | no | Gemini: endpoint OpenAI-compatible de Google |

### Ejecutar

```bash
cd discrete_structure_tool
python -m benchmark.run_loop --limit 3    # prueba rápida (3 casos × 2 sets = 6 llamadas)
python -m benchmark.run_loop              # 30 casos completos
python -m benchmark.run_loop --mode reference  # solo tests, sin API
pytest tests/test_benchmark.py tests/test_extract.py tests/test_pipeline.py -v
```

Las respuestas LLM se cachean en `benchmark/data/responses/{no_tool,with_tool}/`.
La capa 3 de cumplimiento usa siempre DiscreteStructureTool (`validate.py`).

## License

MIT (prototype).
