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
```

**Cursor** — copy `examples/mcp/cursor.json` to `.cursor/mcp.json` and set `cwd` to your clone path. Enable under Settings → Tools & MCP.

**Claude Desktop** — merge `examples/mcp/claude_desktop.json` into your config (adjust `cwd`).

This is a **local stdio mockup**, not a hosted MCP product. For ChatGPT you would need an HTTPS deployment separately.

## Layout

```
src/discrete_structure_tool/   core engine
src/discretevalidator/         thin MCP wrapper
tests/                         unit + integration tests
examples/mcp/                  sample MCP configs
```

## Try it (no MCP)

Ask any LLM:

> ¿Cuántas **r** hay en **strawberry**?

Then verify with the library (answer: **3**, positions `[2, 7, 8]`).

## License

MIT
