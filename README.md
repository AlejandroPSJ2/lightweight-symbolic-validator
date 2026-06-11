# Lightweight Symbolic Validator

A small **proof-of-concept** library that lets AI assistants answer symbolic questions **exactly** — not by guessing.

It works on generic data structures:

- **Text / lists** — count characters, find positions, spot repeats
- **Sets** — union, difference, “what is missing?”
- **Tables / relations** — filter columns, group rows, find duplicate keys

Same JSON API from Python or from a **local MCP mockup** (Cursor / Claude Desktop).

**Repo:** https://github.com/AlejandroPSJ2/lightweight-symbolic-validator

## Who is this for?

| You want to… | Example |
|--------------|---------|
| Count something in text | “How many times does **X** appear in this word or list?” |
| Compare two lists | “Which IDs are in list A but not in list B?” |
| Check a table | “Are there duplicate owners / duplicate rows?” |

The tool does **not** know your domain (medicine, finance, games, etc.). You pass **your** lists and tables; it returns a precise **result** plus **witness** evidence (positions, missing items, duplicates).

## Install

```bash
git clone https://github.com/AlejandroPSJ2/lightweight-symbolic-validator.git
cd lightweight-symbolic-validator
pip install -e ".[dev]"
pytest
```

MCP (optional):

```bash
pip install -e ".[mcp]"
```

## Python — three typical calls

```python
from discretevalidator import validate_discrete_structure

# 1) Text / sequence — exact count + where it appeared
validate_discrete_structure({
    "kind": "sequence",
    "operation": "frequency",
    "a": list("bookkeeper"),
    "target": "e",
})
# → result: 3, witness includes character positions

# 2) Sets — items in A that are not in B
validate_discrete_structure({
    "kind": "set",
    "operation": "difference",
    "a": ["invoice-1", "invoice-2", "invoice-3"],
    "b": ["invoice-1", "invoice-3"],
})
# → result: ["invoice-2"]

# 3) Table / relation — duplicate values in a column
validate_discrete_structure({
    "kind": "relation",
    "operation": "duplicates",
    "a": [
        {"task": "T1", "owner": "Ana"},
        {"task": "T2", "owner": "Ana"},
        {"task": "T3", "owner": "Luis"},
    ],
    "keys": ["owner"],
})
# → witness lists duplicate owners and which rows
```

Same engine: `from discrete_structure_tool import run_tool` (identical payloads).

## JSON API (for developers)

Every call uses the same shape:

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

| Kind | What it models | Example operations |
|------|----------------|-------------------|
| **sequence** | Ordered text or list | count, positions, duplicates |
| **set** | Unique items | union, intersection, difference, coverage |
| **multiset** | Items with repetition | frequency, subset checks |
| **relation** | Rows / tables | project, group_by, join, duplicates |

Response: `{"result": <value>, "witness": {...}}` — the witness is optional proof the model can cite.

## MCP mockup (local)

Exposed tool: **`validate_discrete_structure`** — same JSON as above, callable from an AI agent.

```bash
python -m discretevalidator.mcp_server
# or: discretevalidator-mcp   (after pip install -e ".[mcp]")
```

1. Copy `examples/mcp/mcp.json` → `.cursor/mcp.json` (or Claude Desktop config).
2. Set `cwd` to your clone path (see `examples/mcp/README.md`).
3. Enable the server in Cursor → Settings → Tools & MCP.

After `pip install -e ".[mcp]"`, `examples/mcp/installed.json` works without `cwd`.

Local stdio mockup only — not a hosted cloud service.

## Try it without code

Pick **any** of these prompts in ChatGPT / Claude, then verify with the library or MCP:

1. **Text:** “How many times does the letter **e** appear in **bookkeeper**?”
2. **Sets:** “List **A = {1,2,3,4}** minus **B = {2,4}**.”
3. **Table:** “In this list of `{task, owner}` rows, is any **owner** assigned twice?”

If the model answers from memory, run the same check through `validate_discrete_structure` — you get a reproducible answer and evidence.

## Project layout

```
src/discrete_structure_tool/   core engine
src/discretevalidator/         MCP wrapper
tests/                         unit + integration tests
examples/mcp/                  MCP config samples
```

## License

MIT
