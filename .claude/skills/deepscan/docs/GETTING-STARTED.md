# Getting Started with DeepScan

> By the end of this guide, you will have scanned a project and reviewed findings with file:line evidence.

## Prerequisites

- **Claude Code** installed and working
- **Python 3.10+** (`python3 --version` to check)
- **pydantic** (`pip install pydantic`)
- **Poetry** (for CLI verification; install via `pip install poetry`) -- or use `python3` directly instead of `poetry run python`
- A project with 10+ source files to scan

Optional dependencies for enhanced features:

| Package | Feature | Install |
|---------|---------|---------|
| `tree-sitter-language-pack` | Semantic (AST-based) chunking | `pip install tree-sitter-language-pack` |
| `xxhash` | Faster incremental file hashing | `pip install xxhash` |
| `rich` | Styled error output | `pip install rich` |
| `psutil` | Memory-aware chunking | `pip install psutil` |

## Environment Note

DeepScan operates in two environments. Understanding the difference is important before your first scan.

| Feature | CLI | Claude Code |
|---------|-----|-------------|
| init, status, list, resume, abort, clean | Yes | Yes |
| scout (peek, grep) | Yes | Yes |
| chunk (write_chunks) | Yes | Yes |
| map (parallel analysis) | Placeholders only | Full sub-agent processing |
| reduce (aggregate findings) | Placeholder data | Real aggregation |
| export-results | Yes | Yes |
| Natural language triggers | No | Yes |

The **MAP phase** requires the Claude Code environment to produce real analysis. In CLI mode, `map` generates placeholder results for testing and debugging. Use `map --instructions` to get prompts you can execute manually with the Task tool.

## Step 1: Install DeepScan

```bash
claude plugin add idnotbe/deepscan
```

Or clone manually:

```bash
git clone https://github.com/idnotbe/deepscan.git
# Copy .claude/ and .claude-plugin/ directories to your project
```

Verify the installation:

```bash
poetry run python .claude/skills/deepscan/scripts/deepscan_engine.py --help
```

Expected output:

```
usage: deepscan_engine.py {init,status,exec,reset,export-results,list,resume,abort,clean,map,progress,reduce} ...
```

Verify Python dependencies:

```bash
python3 --version   # Must be 3.10+
python3 -c "import pydantic; print(pydantic.__version__)"
```

## Step 2: Initialize a Scan

```bash
poetry run python .claude/skills/deepscan/scripts/deepscan_engine.py init ./src -q "Find security vulnerabilities"
```

Or in Claude Code:

```
/deepscan init ./src -q "Find security vulnerabilities"
```

Expected output:

```
[OK] DeepScan initialized
  Session: deepscan_1739700000_a1b2c3d4e5f6g7h8
  Context: /home/user/project/src
  Size: 245,832 characters
  Files: 47
```

DeepScan loaded all files from `./src` into external storage. The content is not in the LLM context window -- it is stored on disk at `~/.claude/cache/deepscan/{session_hash}/`.

## Step 3: Explore with Scout

> **How to run commands**: Steps 3-7 use DeepScan subcommands. In **Claude Code**, type them directly (e.g., `exec -c "..."`). In **CLI mode**, prefix with `poetry run python .claude/skills/deepscan/scripts/deepscan_engine.py` (e.g., `poetry run python .claude/skills/deepscan/scripts/deepscan_engine.py exec -c "..."`).

Use the REPL helpers to inspect the loaded context before chunking.

```bash
# View first 3000 characters
exec -c "print(peek_head(3000))"
```

You will see file content with headers like `=== FILE: src/app.py ===`.

```bash
# Check total context size
exec -c "print(f'Context: {context_length()} chars')"
```

Expected output: `Context: 245832 chars`

```bash
# Search for patterns
exec -c "print(grep('TODO|FIXME', max_matches=10))"
```

Returns a list of match dicts with `match`, `span`, and `snippet` keys.

## Step 4: Create Chunks

Split the context into manageable pieces for parallel processing.

```bash
exec -c "paths = write_chunks(size=150000); print(f'{len(paths)} chunks created')"
```

Expected output:

```
[INFO] Using dynamic timeout: 30s for 245,832 bytes
2 chunks created
```

Chunks are written to `~/.claude/cache/deepscan/{session_hash}/chunks/`.

## Step 5: Run MAP Phase

In Claude Code:

```bash
map
```

Each chunk is processed by a sub-agent that analyzes it according to your query. You will see progress as batches complete.

In CLI mode, you will see placeholder results:

```
[WARN] Running in CLI-only mode. Sub-agents require Claude Code environment.
[MAP] Processing batch 1/1 (2 chunks)
[MAP] Batch 1: 0 success, 2 placeholders, 0 failed
```

For manual control, use `map --instructions` to get prompts you can feed to the Task tool yourself.

## Step 6: Reduce and Review

Aggregate findings from all chunks:

```bash
reduce
```

Expected output:

```
[OK] Aggregation complete
  Total findings: 12
  Unique findings: 8
  Deduplication ratio: 33.3%
  Contradictions: 1
```

The reduce phase deduplicates similar findings (Jaccard similarity threshold 0.7) and flags contradictions where sub-agents disagreed.

## Step 7: Export Results

```bash
export-results findings.json
```

The exported JSON contains structured findings:

```json
{
  "session_id": "deepscan_1739700000_a1b2c3d4e5f6g7h8",
  "query": "Find security vulnerabilities",
  "results": [
    {
      "chunk_id": "a1b2c3d4",
      "status": "completed",
      "findings": [
        {
          "point": "SQL injection vulnerability",
          "evidence": "Line 45: query = f\"SELECT * FROM users WHERE id={user_id}\"",
          "confidence": "high",
          "location": {"file": "src/db.py", "line": 45}
        }
      ]
    }
  ]
}
```

Each finding has:

| Field | Meaning |
|-------|---------|
| `point` | What was found |
| `evidence` | Supporting code or text |
| `confidence` | `high`, `medium`, or `low` |
| `location` | File path and line number |

Open the referenced file at the specified line to verify each finding.

## What's Next

- [Troubleshooting](TROUBLESHOOTING.md) -- fix common errors and learn workflow recipes
- [Use Cases](USE_CASES.md) -- lazy mode, targeted scanning, incremental analysis
- [Reference](REFERENCE.md) -- complete command, configuration, and REPL sandbox reference
- [Error Codes](ERROR-CODES.md) -- all DS-NNN error codes with causes and fixes

> **Tip**: Use `--agent-type security` for vulnerability-focused analysis, or `--agent-type architecture` for design reviews. See the [Reference](REFERENCE.md#specialized-agent-types) for all agent types.
