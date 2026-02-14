---
name: deepscan
description: |
  Performs deep, multi-file analysis for complex tasks where standard context
  windows fail or "context rot" occurs. Orchestrates parallel sub-agents
  (security, architecture, performance specialized) to trace data flows,
  audit vulnerabilities, and map dependencies across modules. Best for
  "multi-hop" reasoning requiring evidence synthesis from distributed sources.

  Use when: analyzing entire project architecture, performing security audits
  across many files, tracing data flow through multiple modules, investigating
  how components interact, understanding legacy system structure, aggregating
  findings with precise file:line evidence.

  Do NOT use for: single-file lookups (use Grep), file discovery (use Glob),
  reading 1-3 specific files (use Read), small-context tasks, simple pattern matching.

triggers:
  - "/deepscan"
  - "analyze large codebase"
  - "scan entire project"
  - "trace data flow"
  - "security audit across"
  - "architecture review"
  - "cross-file investigation"
  - "how does this flow through"
  - "understand the whole system"
  - "multi-module analysis"

allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Task
  - Grep
  - Glob
---

# DeepScan Skill

> **Purpose**: Prevent Context Rot via chunked map-reduce analysis.

> **IMPORTANT**: Full sub-agent processing requires **Claude Code environment**.
> CLI-only usage produces placeholder results for debugging/exploration only.
> Use `map --instructions` to get prompts for manual Task tool execution.

**NOT appropriate for:** Single-file searches (use Grep), file discovery (use Glob), reading 1-3 files (use Read), small-context tasks.

## Quick Reference

| Mode | Command | Use Case | Environment |
|------|---------|----------|-------------|
| Full | `init <path>` | Small-medium projects | Claude Code for analysis |
| Lazy | `init <path> --lazy` | Large codebases, explore first | CLI for exploration |
| Targeted | `init <path> --target <file>` | Specific files only | Claude Code for analysis |

> **Note**: The `map` command performs actual analysis only in Claude Code environment.
> In CLI mode, it generates placeholder results for testing/debugging.

## Core Workflow

### 1. Initialize

```bash
poetry run python .claude/skills/deepscan/scripts/deepscan_engine.py init <path> [-q "query"] [--adaptive]
```

**Flags:**
- `--adaptive`: Content-type chunk sizing (code=100K, config=80K, docs=200K)
- `--lazy`: Structure only, load on-demand
- `--target PATH`: Specific files/directories (can repeat)

### 2. Scout

```bash
# Explore context
exec -c "print(peek_head(5000))"
exec -c "print(grep('TODO|FIXME', max_matches=50))"
exec -c "print(f'Context: {context_length()} chars')"
```

### 3. Chunk

```bash
exec -c "paths = write_chunks(size=150000, overlap=10000); print(f'{len(paths)} chunks')"
```

### 4. MAP (Parallel Processing)

```bash
# Auto parallel processing
map [--escalate]

# Manual mode (get prompts for Task tool)
map --instructions
```

### 5. REDUCE (Aggregate)

```bash
# Check progress
progress

# Export results
export-results output.json
```

### 6. Session Management

```bash
list                    # All sessions
resume [hash]           # Continue session
status                  # Current status
abort <hash>            # Delete session
clean --older-than 7    # Remove old sessions
```

## Helper Functions (REPL)

| Function | Description |
|----------|-------------|
| `peek(start, end)` | View context slice |
| `peek_head(n)` / `peek_tail(n)` | First/last n chars |
| `grep(pattern, max_matches, window)` | Regex search |
| `grep_file(pattern, filepath)` | Search specific file (lazy mode) |
| `write_chunks(size, overlap)` | Create chunk files |
| `add_result(result)` | Record chunk findings |
| `get_status()` | State summary |
| `context_length()` | Total characters |

**Lazy Mode Helpers:**
| Function | Description |
|----------|-------------|
| `is_lazy_mode()` | Check if lazy mode active |
| `get_tree_view()` | Directory tree structure |
| `preview_dir(subpath)` | Preview subdirectory |
| `load_file(filepath)` | Load specific file |

## Specialized Agents

| Type | Focus |
|------|-------|
| `general` | Broad code analysis (default) |
| `security` | Vulnerabilities, credentials, injections |
| `architecture` | Design patterns, coupling, dependencies |
| `performance` | Bottlenecks, complexity, efficiency |

## Result Recording

```python
add_result({
    "chunk_id": "chunk_0001",
    "status": "completed",  # completed, partial, failed
    "findings": [{
        "point": "Found SQL injection",
        "evidence": "Line 45: query = f'SELECT * FROM {user_input}'",
        "confidence": "high",  # high, medium, low
        "location": {"file": "app.py", "line": 45}
    }],
    "missing_info": [],
    "partial_answer": None
})
```

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `chunk_size` | 150000 | Chars per chunk (50K-300K) |
| `chunk_overlap` | 0 | Overlap between chunks |
| `max_parallel_agents` | 5 | Sub-agents per batch |
| `timeout_seconds` | 300 | Sub-agent timeout |
| `enable_escalation` | True | haiku→sonnet on failures |

## Model Escalation

Automatic upgrade from haiku to sonnet on quality/complexity failures.
- Budget: Max 15% chunks, $5 sonnet cap
- Enable: `map --escalate`

## Key Features

- **Checkpoints**: Auto-save after each batch, resume on failure
- **Progress Streaming**: `tail -f ~/.claude/cache/deepscan/{hash}/progress.jsonl`
- **Deduplication**: Similarity threshold 0.7
- **Incremental**: Delta analysis via file hash manifest (3-10x faster)

## Security

- JSON-only serialization (no pickle)
- Sandboxed REPL (restricted builtins, AST validation)
- File limits: 10MB/file, 50MB total
- Path traversal protection

## Troubleshooting

| Error | Solution |
|-------|----------|
| "No state found" | Run `init` first |
| "Forbidden pattern" | Use allowed helpers, not `__import__` |
| "File too large" | Files >10MB skipped |
| Windows Unicode | Set `$env:PYTHONIOENCODING='utf-8'` |

## References

- **Use Cases**: See `docs/USE_CASES.md` for detailed scenarios
- **Architecture**: See `docs/ARCHITECTURE.md`
- **Security**: See `docs/SECURITY.md`
