# Lightweight Symbolic Validator

A small **proof-of-concept** library that lets AI assistants answer symbolic questions **exactly** — not by guessing.

It works on generic data structures:

- **Text / lists** — count characters, find positions, spot repeats
- **Sets** — union, difference, “what is missing?”
- **Tables / relations** — filter columns, group rows, find duplicate keys

Same JSON API from Python or from a **local MCP mockup** (Cursor / Claude Desktop).

**Repo:** https://github.com/AlejandroPSJ2/lightweight-symbolic-validator

## Who is this for?

For anyone wiring an **LLM agent** (Cursor, Claude Desktop, custom apps) who is tired of silent math mistakes: wrong letter counts, set logic off by one, missed duplicates in a table.

**Without a tool**, the model guesses those steps in its head — and often gets them wrong.

**With this tool or MCP enabled**, the agent can delegate those steps to deterministic code. You do not need to hand-craft a call for each niche scenario; whenever the model would reason symbolically (counts, differences, coverage, duplicates), it can reach for `validate_discrete_structure` instead. In practice that means:

- fewer wrong counts and “obvious” arithmetic slips in answers
- fewer set/table mistakes (missing items, unseen duplicates)
- answers backed by **witness** data when the tool was used

It is **not** tied to one domain or one demo word. The same API covers text, lists, sets, and tables — whatever data the conversation already has.

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
