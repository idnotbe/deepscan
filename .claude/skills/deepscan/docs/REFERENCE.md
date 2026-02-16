# DeepScan Reference

Complete lookup reference for all commands, configuration, REPL sandbox rules, and file locations.

## Commands

### init

Initialize a new scan session.

```
init <context_path> [-q QUERY] [--adaptive] [--incremental] [--previous-session HASH]
     [--lazy] [--target PATH] [--depth N] [--agent-type TYPE] [--force]
```

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `context_path` | positional | required | Path to file or directory to analyze |
| `-q/--query` | string | None | Analysis question |
| `-a/--adaptive` | flag | False | Auto-detect content type for chunk sizing |
| `--incremental` | flag | False | Only process files changed since previous session |
| `--previous-session` | string | None | Session hash for incremental comparison |
| `--lazy` | flag | False | Load structure only, no file contents |
| `--target` | string (repeatable) | None | Specific paths to include |
| `--depth` | int | 3 | Max directory depth in lazy mode |
| `--agent-type` | choice | `general` | Analysis specialization (see [Agent Types](#specialized-agent-types)) |
| `--force` | flag | False | Overwrite existing active session |

### exec

Execute a sandboxed Python expression against the loaded context.

```
exec -c CODE [--timeout N]
```

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `-c/--code` | string | required | Python code to execute |
| `-t/--timeout` | int | auto | Execution timeout in seconds |

Timeout defaults: 5 seconds for simple commands, 30-120 seconds for `write_chunks` (auto-calculated from context size at 2s/MB).

### map

Run the MAP phase: process chunks through sub-agents.

```
map [-i/--instructions] [-e/--escalate] [-o/--output FILE] [--batch N] [--limit N]
```

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `-i/--instructions` | flag | False | Output Task tool prompts instead of processing |
| `-e/--escalate` | flag | False | Retry failed chunks with sonnet model |
| `-o/--output` | string | None | Write instructions to file |
| `--batch` | int | None | Show specific batch only (1-indexed) |
| `--limit` | int | 5 | Max chunks per instruction page |

### reduce

Run the REDUCE phase: aggregate findings from all chunks with deduplication and contradiction detection.

```
reduce
```

Outputs:
- Total findings (before deduplication)
- Unique findings (after deduplication at 0.7 similarity threshold)
- Deduplication ratio
- Contradictions detected (via bidirectional negation heuristic)

### export-results

Export results to a JSON file.

```
export-results <output_path>
```

### status

Show current session status.

```
status
```

### progress

Show or monitor scan progress.

```
progress [--watch]
```

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--watch` | flag | False | Real-time monitoring (polls every 2 seconds) |

### list

List all sessions sorted by modification time (newest first).

```
list
```

### resume

Resume an interrupted session.

```
resume [session_hash]
```

If no hash is provided, resumes the most recent session.

### abort

Permanently delete a session and all its data (chunks, results, checkpoints).

```
abort <session_hash>
```

### clean

Remove old sessions based on age.

```
clean [--older-than DAYS]
```

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--older-than` | int | 7 | Delete sessions older than N days |

Also enforces a 1GB total size cap via LRU eviction.

### reset

Reset the current session.

```
reset
```

---

## CLI Shortcuts

| Shortcut | Expands to | Description |
|----------|------------|-------------|
| `?` | `status` | Show current session status |
| `! "code"` | `exec -c "code"` | Execute REPL expression |
| `+` | `resume` | Resume most recent session |
| `+ hash` | `resume hash` | Resume specific session |
| `x hash` | `abort hash` | Abort (delete) a session |
| `<path>` | `init <path>` | Initialize scan on path (if path exists on disk) |

---

## CLI vs Claude Code Environment

| Feature | CLI | Claude Code |
|---------|-----|-------------|
| init (load context) | Yes | Yes |
| scout (peek, grep) | Yes | Yes |
| chunk (write_chunks) | Yes | Yes |
| map (parallel analysis) | Placeholders only | Full sub-agent processing |
| reduce (aggregate) | Placeholder data | Real aggregation |
| export-results | Yes | Yes |
| progress / status / list | Yes | Yes |
| Natural language triggers | No | Yes |

---

## Configuration Settings

Configuration is set via **CLI flags** on the `init` command and **function parameters** on REPL helpers. There is no external configuration file. Settings are stored in the session's `state.json` as part of the `DeepScanConfig` Pydantic model.

**How to set values:**
- `chunk_size`, `chunk_overlap`: Pass to `write_chunks(size=..., overlap=...)`
- `adaptive_chunking`: Use `--adaptive` flag on `init`
- `scan_mode`: Use `--lazy` or `--target` flags on `init`
- `agent_type`: Use `--agent-type` flag on `init`
- `incremental_enabled`, `previous_session`: Use `--incremental` and `--previous-session` flags on `init`
- `max_parallel_agents`, `max_retries`, `timeout_seconds`, `enable_escalation`, `max_escalation_ratio`, `max_sonnet_cost_usd`: Pydantic defaults; currently not exposed as CLI flags (modify `DeepScanConfig` in `models.py` for custom defaults)

| Setting | Default | Range | Description |
|---------|---------|-------|-------------|
| `chunk_size` | 150,000 | 50,000 - 300,000 | Characters per chunk |
| `chunk_overlap` | 0 | 0 - 50,000 (must be < chunk_size) | Overlap between chunks |
| `max_parallel_agents` | 5 | 1-20 | Sub-agents per batch |
| `max_retries` | 3 | -- | Retry count per chunk |
| `timeout_seconds` | 300 | 30-3600 | Sub-agent timeout (seconds) |
| `enable_escalation` | True | boolean | haiku to sonnet on failures |
| `max_escalation_ratio` | 0.15 | 0.0-1.0 | Max 15% of chunks escalated |
| `max_sonnet_cost_usd` | 5.0 | -- | Sonnet cost cap per session |
| `agent_type` | `general` | general/security/architecture/performance | Analysis specialization |
| `adaptive_chunking` | False | boolean | Content-type chunk sizing |
| `scan_mode` | FULL | FULL/LAZY/TARGETED | Context loading strategy |
| `lazy_depth` | 3 | -- | Max lazy mode directory depth |
| `lazy_file_limit` | 50 | -- | Max files displayed in lazy mode |

---

## Specialized Agent Types

Each agent type provides specialized system instructions to sub-agents.

| Type | Flag | Focus | Verification Rules | Example Query |
|------|------|-------|--------------------|---------------|
| `general` | `--agent-type general` | Broad analysis | Standard evidence required | "Review code quality" |
| `security` | `--agent-type security` | Vulnerabilities, credentials, injection | Cross-reference with OWASP; verify exploitability | "Find SQL injection and XSS" |
| `architecture` | `--agent-type architecture` | Design patterns, coupling, dependencies | Verify with dependency graph evidence | "Find circular dependencies" |
| `performance` | `--agent-type performance` | Bottlenecks, complexity, N+1 queries | Verify with complexity analysis | "Find N+1 queries" |

---

## REPL Sandbox

### Safe Builtins (36 entries)

The following Python builtins are available in the REPL:

`len`, `str`, `int`, `float`, `bool`, `list`, `dict`, `tuple`, `set`, `print`, `range`, `enumerate`, `zip`, `map`, `filter`, `min`, `max`, `sum`, `sorted`, `reversed`, `abs`, `round`, `isinstance`, `type`, `repr`, `True`, `False`, `None`, `all`, `any`, `slice`, `dir`, `vars`, `hasattr`, `callable`, `id`

### Allowed Syntax

| Category | Examples |
|----------|----------|
| Arithmetic | `+`, `-`, `*`, `/`, `//`, `%`, `**` |
| Comparisons | `==`, `!=`, `<`, `>`, `<=`, `>=`, `in`, `not in` |
| Boolean | `and`, `or`, `not` |
| String operations | `.upper()`, `.split()`, `.startswith()`, f-strings |
| Collections | list, dict, set, tuple creation and methods |
| Comprehensions | `[x for x in data]`, `{k: v for ...}`, `{x for ...}` |
| Lambda | `lambda x: x > 0` |
| Ternary | `x if condition else y` |
| Variable assignment | `x = 5`, `x += 1` |
| For loops and if statements | `for x in data:`, `if x > 0:` |
| Keyword arguments | `func(key=value)` |

### Blocked Operations

| Category | Examples | Reason |
|----------|----------|--------|
| Imports | `import os`, `__import__('os')` | System access |
| Dynamic dispatch | `getattr()`, `setattr()`, `delattr()` | Bypasses AST filtering |
| Code execution | `exec()`, `eval()`, `compile()` | Arbitrary code execution |
| File I/O | `open()` | Filesystem access |
| OS access | `os.*`, `subprocess.*`, `sys.*` | System-level operations |
| Dunder attributes | `__class__`, `__globals__`, `__bases__`, etc. | Sandbox escape |
| Any `_`-prefixed attribute | `obj._private` | Internal access |
| Function/class definitions | `def func():`, `class Foo:` | Hidden complexity |
| Exception handling | `try:`, `raise`, `with:` | Control flow manipulation |
| Generators/async | `yield`, `await`, `async` | Generator/async abuse |
| `re` module | `re.search()` | Removed (CVE-2026-002); use `grep()` helper |

### Forbidden Patterns (Layer 1)

These 15 regex patterns are checked before any code executes:

`__import__`, `exec\s*\(`, `eval\s*\(`, `compile\s*\(`, `open\s*\(`, `os\.`, `subprocess`, `sys\.`, `__globals__`, `__class__`, `__bases__`, `__closure__`, `getattr\s*\(`, `setattr\s*\(`, `delattr\s*\(`

### Blocked AST Nodes (Layer 2)

Only explicitly whitelisted AST nodes are allowed. Blocked nodes include: `FunctionDef`, `ClassDef`, `AsyncFunctionDef`, `Import`, `ImportFrom`, `Global`, `Nonlocal`, `Yield`, `YieldFrom`, `Await`, `Try`, `Raise`, `With`, `Assert`, `Match`.

### Blocked Attributes (Layer 3)

All `_`-prefixed attributes plus these 19 specific dunders: `__class__`, `__bases__`, `__subclasses__`, `__mro__`, `__globals__`, `__code__`, `__closure__`, `__func__`, `__self__`, `__dict__`, `__doc__`, `__module__`, `__builtins__`, `__import__`, `__loader__`, `__spec__`, `__annotations__`, `__wrapped__`, `__qualname__`.

---

## Helper Functions

### Full Mode Helpers

| Function | Signature | Returns | Description |
|----------|-----------|---------|-------------|
| `peek` | `(start=0, end=None)` | `str` | View context substring (capped at 50KB) |
| `peek_head` | `(n=3000)` | `str` | First n characters |
| `peek_tail` | `(n=3000)` | `str` | Last n characters |
| `grep` | `(pattern, max_matches=20, window=100)` | `list[dict]` | Regex search with ReDoS protection |
| `grep_file` | `(pattern, filepath, max_matches=20, window=100)` | `list[dict]` | Search a specific file (works in lazy mode too) |
| `chunk_indices` | `(size=150000, overlap=0)` | `list[tuple]` | Calculate chunk boundaries without writing |
| `write_chunks` | `(out_dir=None, size=150000, overlap=0, semantic=False)` | `list[str]` | Create chunk files; `semantic=True` for AST-based |
| `context_length` | `()` | `int` | Total context characters |
| `add_buffer` | `(text)` | None | Add note to buffer |
| `get_buffers` | `()` | `list[str]` | Get all buffered notes |
| `clear_buffers` | `()` | None | Clear all buffers |
| `add_result` | `(result)` | None | Record a chunk result (validated as ChunkResult) |
| `add_results_from_file` | `(file_path)` | `dict` | Batch import from JSON (max 10MB). Returns `{added, errors}` |
| `set_phase` | `(phase)` | None | Set workflow phase |
| `set_final_answer` | `(answer)` | None | Set final answer, mark 100% complete |
| `get_status` | `()` | `dict` | Session summary (id, phase, context_size, chunks, progress) |

### Lazy Mode Helpers

| Function | Signature | Returns | Description |
|----------|-----------|---------|-------------|
| `is_lazy_mode` | `()` | `bool` | Check if lazy mode is active |
| `get_tree_view` | `()` | `str` | Directory tree structure |
| `preview_dir` | `(subpath, max_depth=2, max_files=30)` | `str` | Preview subdirectory |
| `load_file` | `(filepath)` | `str` | Load file content (max 10MB, binary detection) |

> `get_tree_view()`, `preview_dir()`, and `load_file()` work in both lazy and full mode.

---

## Size Limits

| Limit | Value | Enforcement |
|-------|-------|-------------|
| Single file | 10MB | Files over 10MB are skipped during init |
| Total context | 50MB | DS-304 error if exceeded |
| REPL code input | 100KB | Code truncated at 100,000 characters |
| REPL output per operation | 500KB | Output truncated with informative suffix |
| CLI display | 100KB | CLI output capped |
| Context preview (peek) | 50KB | Preview operations capped |
| Grep content per search | 5MB | Grep operations capped |
| Import file (add_results_from_file) | 10MB | File size check before read |
| Load file (load_file helper) | 10MB | File size check before read |
| Checkpoint write | 20MB | Warns if exceeded |
| Checkpoint read | 100MB | DoS protection (asymmetric for backward compatibility) |
| Progress file | 10MB | Auto-rotates to `.jsonl.1` at limit |
| Session cache total | 1GB | GC cleans oldest sessions via TTL (7 days) + LRU |

### Resource Limits (Unix Only)

| Resource | Soft Limit | Hard Limit |
|----------|------------|------------|
| Memory | 256MB | 512MB |
| CPU time | 60 seconds | 120 seconds |
| File size | 10MB | 10MB |

> These limits use the Unix `resource` module and are **not enforced on Windows**. On Windows, the sandbox runs with degraded protection.

---

## Timeouts

| Scope | Default | Range | Configuration |
|-------|---------|-------|---------------|
| REPL execution | 5s | -- | `exec --timeout N` |
| Chunking (write_chunks) | 30-120s (auto) | min 30s, max 120s | Auto: 2s per MB of context |
| Grep (ReDoS protection) | 10s | -- | `GREP_TIMEOUT` in constants.py |
| Sub-agent processing | 300s | 30-3600s | `timeout_seconds` in config |
| Graceful cancellation | 30s | -- | `graceful_timeout` parameter (map command) |
| Progress watch polling | 2s | -- | `WATCH_POLL_INTERVAL` in constants.py |

---

## Adaptive Chunk Sizes

When `--adaptive` is enabled, chunk sizes are determined by the dominant file extension:

| Category | Extensions | Chunk Size |
|----------|------------|------------|
| Code | `.py`, `.java`, `.ts`, `.tsx`, `.js`, `.jsx`, `.go`, `.rs`, `.c`, `.cpp`, `.h`, `.hpp`, `.cs`, `.rb`, `.php`, `.swift`, `.kt` | 100,000 |
| Config | `.json`, `.yaml`, `.yml`, `.toml` | 80,000 |
| Structured | `.xml`, `.sql` | 100,000 |
| Docs | `.md`, `.rst` | 200,000 |
| Docs | `.html` | 150,000 |
| Docs | `.txt` | 250,000 |
| Default | (other) | 150,000 |

---

## Default Excluded Directories

These 19 directories are auto-pruned during file traversal:

`node_modules`, `.git`, `.svn`, `.hg`, `__pycache__`, `.venv`, `venv`, `.env`, `env`, `.tox`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `dist`, `build`, `.next`, `.nuxt`, `target`, `vendor`

Add custom exclusions via `.deepscanignore`. See [Troubleshooting: How to Exclude Files](TROUBLESHOOTING.md#how-to-exclude-files-deepscanignore).

---

## Model Escalation

| Parameter | Value |
|-----------|-------|
| Default model | haiku |
| Escalation model | sonnet |
| Max escalated chunks | 15% of total |
| Sonnet budget cap | $5 per session |
| Trigger conditions | `QUALITY_LOW` or `COMPLEXITY` failure after attempt >= 2 |
| Sequential fallback | After 2 consecutive batches with >50% failure rate |

---

## File Locations

| File | Path | Purpose |
|------|------|---------|
| Session state | `~/.claude/cache/deepscan/{hash}/state.json` | Main session state |
| Checkpoint | `~/.claude/cache/deepscan/{hash}/checkpoint.json` | Recovery point |
| Chunks | `~/.claude/cache/deepscan/{hash}/chunks/` | Chunk text files |
| Results | `~/.claude/cache/deepscan/{hash}/results/` | Sub-agent result files |
| Progress | `~/.claude/cache/deepscan/{hash}/progress.jsonl` | Real-time event log |
| Current session marker | `~/.claude/cache/deepscan/.current_session` | Active session hash |

### Session ID Format

```
deepscan_{unix_timestamp}_{16_hex_chars}
```

The random suffix uses `secrets.token_hex(8)` for cryptographic randomness.

---

## Natural Language Triggers

These phrases activate DeepScan in Claude Code:

- `/deepscan`
- "analyze large codebase"
- "scan entire project"
- "trace data flow"
- "security audit across"
- "architecture review"
- "cross-file investigation"
- "how does this flow through"
- "understand the whole system"
- "multi-module analysis"

---

## See Also

- [Getting Started](GETTING-STARTED.md) -- step-by-step tutorial
- [Error Codes](ERROR-CODES.md) -- all DS-NNN error codes
- [Security](SECURITY.md) -- threat model and defense-in-depth architecture
- [Troubleshooting](TROUBLESHOOTING.md) -- common errors and workflow recipes
