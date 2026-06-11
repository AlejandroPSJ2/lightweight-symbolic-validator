# Lightweight Symbolic Validator

Proof-of-concept: give LLM agents **deterministic** symbolic checks instead of mental arithmetic over strings, sets, and tables.

One JSON API. Optional **MCP server mockup** for Cursor / Claude Desktop (stdio, local).

**Repo:** https://github.com/AlejandroPSJ2/lightweight-symbolic-validator

## Install

```bash
git clone https://github.com/AlejandroPSJ2/lightweight-symbolic-validator.git
cd lightweight-symbolic-validator
pip install -e ".[dev]"
pytest
```

With MCP (optional):

```bash
pip install -e ".[mcp]"
```

## Python

```python
from discretevalidator import validate_discrete_structure

validate_discrete_structure({
    "kind": "sequence",
    "operation": "frequency",
    "a": list("strawberry"),
    "target": "r",
})
# {'result': 3, 'witness': {'positions': [2, 7, 8], 'counts': {'r': 3}}}
```

Same engine via `from discrete_structure_tool import run_tool`.

## JSON API

```json
{
  "kind": "sequence | set | multiset | relation",
  "operation": "...",
  "a": [...],
  "b": [...],
  "target": "...",
  "keys": [...]
}
```

| Kind | Operations |
|------|------------|
| sequence | `frequency`, `count`, `positions`, `membership`, `deduplicate`, `duplicates` |
| set | `union`, `intersection`, `difference`, `symmetric_difference`, `subset`, `superset`, `membership`, `coverage`, `duplicates` |
| multiset | `frequency`, `union`, `intersection`, `difference`, `subset`, `superset`, `membership`, `duplicates` |
| relation | `project`, `group_by`, `join`, `duplicates`, `coverage`, `membership` |

Returns `{"result": ..., "witness": {...}}`.

## MCP mockup (local)

Tool name: **`validate_discrete_structure`**

```bash
python -m discretevalidator.mcp_server
# or: discretevalidator-mcp   (after pip install -e ".[mcp]")
```

Copy `examples/mcp/mcp.json` → `.cursor/mcp.json` (Cursor) or merge into Claude Desktop config. Set `cwd` to your clone path. See `examples/mcp/README.md`.

After `pip install -e ".[mcp]"`, you can use `examples/mcp/installed.json` instead (no `cwd` needed).

Local stdio mockup only — not a hosted MCP service.

## Layout

```
src/discrete_structure_tool/   core engine
src/discretevalidator/         thin MCP wrapper
tests/                         unit + integration tests
examples/mcp/                  MCP config samples (see README there)
```

## Try it (no MCP)

Ask any LLM:

> ¿Cuántas **r** hay en **strawberry**?

Then verify with the library (answer: **3**, positions `[2, 7, 8]`).

## License

MIT
