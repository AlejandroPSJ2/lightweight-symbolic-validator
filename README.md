# Lightweight Symbolic Validator

Deterministic symbolic validation for LLM agents over **sequences**, **sets**, **multisets**, and **relations**.

Use it as a **Python library**, an **MCP server** (FastMCP), or via **OpenAI-style function calling**. Same JSON API everywhere.

**Repository:** https://github.com/AlejandroPSJ2/lightweight-symbolic-validator

## Why

LLMs often miscount characters, confuse set logic, or hallucinate join results. This tool offloads those steps to deterministic code and returns verifiable **witnesses** (`positions`, `missing_items`, `duplicate_items`, …).

## Quick install

```bash
git clone https://github.com/AlejandroPSJ2/lightweight-symbolic-validator.git
cd lightweight-symbolic-validator
pip install -e ".[mcp,dev]"
pytest
```

Or install MCP support only:

```bash
pip install -e ".[mcp]"
```

## Python usage

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

Legacy import (same engine):

```python
from discrete_structure_tool import run_tool
run_tool({"kind": "set", "operation": "difference", "a": ["R1","R2"], "b": ["R1"]})
```

## MCP server

Tool exposed to agents: **`validate_discrete_structure`**

### Run manually

```bash
python -m discretevalidator.mcp_server
# or after install:
discretevalidator-mcp
```

### Cursor

Copy `examples/mcp/cursor.json` into your project `.cursor/mcp.json` and set `cwd` to the cloned repo path:

```json
{
  "mcpServers": {
    "lightweight-symbolic-validator": {
      "command": "python",
      "args": ["-m", "discretevalidator.mcp_server"],
      "cwd": "C:/path/to/lightweight-symbolic-validator"
    }
  }
}
```

Enable the server under **Settings → Tools & MCP**, then reload Cursor.

### Claude Desktop

Merge `examples/mcp/claude_desktop.json` into `claude_desktop_config.json` (adjust `cwd`).

After `pip install -e ".[mcp]"`, you can use `examples/mcp/installed.json` with command `discretevalidator-mcp` (no `cwd` needed).

### OpenAI function calling

Register one tool and forward the payload:

```python
from discretevalidator import validate_discrete_structure

def handle_tool_call(name: str, arguments: dict) -> dict:
    if name == "validate_discrete_structure":
        return validate_discrete_structure(arguments["payload"])
    raise ValueError(name)
```

Schema (abbreviated):

```json
{
  "type": "function",
  "function": {
    "name": "validate_discrete_structure",
    "parameters": {
      "type": "object",
      "properties": {
        "payload": {
          "type": "object",
          "properties": {
            "kind": {"type": "string", "enum": ["sequence", "set", "multiset", "relation"]},
            "operation": {"type": "string"},
            "a": {"type": "array"},
            "b": {"type": "array"},
            "target": {},
            "keys": {"type": "array", "items": {"type": "string"}}
          },
          "required": ["kind", "operation", "a"]
        }
      },
      "required": ["payload"]
    }
  }
}
```

## JSON API

```python
validate_discrete_structure({
    "kind": "sequence | set | multiset | relation",
    "operation": "...",
    "a": [...],
    "b": [...],       # optional
    "target": "...",  # optional
    "keys": [...],    # relation ops
    "normalize": {"casefold": true, "trim": true, "nfkc": false}
})
```

| Kind | Operations |
|------|------------|
| **sequence** | `frequency`, `count`, `positions`, `membership`, `deduplicate`, `duplicates` |
| **set** | `union`, `intersection`, `difference`, `symmetric_difference`, `subset`, `superset`, `membership`, `coverage`, `duplicates` |
| **multiset** | `frequency`, `union`, `intersection`, `difference`, `subset`, `superset`, `membership`, `duplicates` |
| **relation** | `project`, `group_by`, `join`, `duplicates`, `coverage`, `membership` |

Returns:

```json
{"result": "<value>", "witness": {"...": "optional evidence"}}
```

## Project layout

```
src/discretevalidator/          MCP wrapper + validate_discrete_structure
src/discrete_structure_tool/    Core symbolic engine (run_tool)
tests/                          Unit + integration tests
examples/mcp/                   Cursor / Claude Desktop configs
benchmark/                      Optional LLM evaluation harness (not required for MCP)
demo_migration_plan.py          Benchmark demo script (domain-specific, optional)
```

## Benchmark (optional)

Research harness comparing LLM accuracy with/without the tool. Requires API keys — see `.env.example`.

```bash
pip install -e ".[benchmark]"
copy .env.example .env   # Windows
python -m benchmark.run_loop --limit 3
```

## Development

```bash
pip install -e ".[dev,mcp]"
pytest
```

## License

MIT — see [LICENSE](LICENSE).
