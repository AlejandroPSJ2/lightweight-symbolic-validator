# Lightweight Symbolic Validator

**Proof-of-concept MCP tool** that helps LLM agents apply deterministic validations for set logic, sequences, multisets and relations. Local PoC

Connect it in **Cursor** or **Claude Desktop** (local, stdio). Once enabled, the tool **`validate_discrete_structure`** is **available** to the agent on every turn — the agent **decides when to call it**; it does not run on every message by itself.

**Repo:** https://github.com/AlejandroPSJ2/lightweight-symbolic-validator

## Who is this for?

For anyone using an **LLM agent** who keeps seeing the same slips: wrong counts, set mistakes, missed duplicates in a table.

| | Without tool | With this MCP enabled |
|---|--------------|------------------------|
| How it works | Model guesses in the reply | Model delegates to deterministic code |
| Typical outcome | Silent errors | Fewer symbolic mistakes; optional **witness** evidence in the answer |

## Example

<img width="604" height="404" alt="image" src="https://github.com/user-attachments/assets/e1c51769-72a1-4911-85b5-724cc599eae9" />

## Quick start (MCP)

```bash
git clone https://github.com/AlejandroPSJ2/lightweight-symbolic-validator.git
cd lightweight-symbolic-validator
pip install -e ".[mcp]"
```

**Cursor**

1. Copy `examples/mcp/mcp.json` → `.cursor/mcp.json`
2. Set `cwd` to your clone path (see `examples/mcp/README.md`)
3. Settings → Tools & MCP → enable **lightweight-symbolic-validator** → reload window

**Claude Desktop** — same JSON, merged into your MCP config (adjust `cwd`).

**Already installed via pip?** Use `examples/mcp/installed.json` (`discretevalidator-mcp`, no `cwd`).

Manual check:

```bash
python -m discretevalidator.mcp_server
```

Local mockup only — not a hosted cloud service.

## Try it

With the MCP **on**, ask your agent things like:

- “How many times does **e** appear in **bookkeeper**?”
- “What is **{1,2,3,4}** minus **{2,4}**?”
- “In this task/owner list, is anyone assigned twice?”

Compare the same prompts **with the tool off**: answers are more likely to drift. With the tool on, the agent should call `validate_discrete_structure` and cite the result.

## What the tool covers (at a glance)

- **Text / lists** — counts, positions, repeats  
- **Sets** — union, difference, what is missing  
- **Tables** — duplicates, grouping, column filters  

One tool name, many operations — the agent picks the payload; you do not hand-write JSON in normal use.

## For developers

This repo includes a small Python library (`discrete_structure_tool` / `discretevalidator`) behind the MCP server. If you embed it in your own app:

```bash
pip install -e ".[dev]"
pytest
```

Implementation lives under `src/`. The README focuses on the **agent + MCP** path; the library is the engine, not the product story.

## License

MIT
