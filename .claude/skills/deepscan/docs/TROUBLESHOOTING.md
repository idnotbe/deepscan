# Troubleshooting and How-To Guides

## Common Errors

### "No state found" / "No active session"

**What you see:** `[ERROR] No active session. Run 'deepscan init <path>' first.`

**Cause:** You ran a command (like `exec`, `status`, or `map`) without an active session.

**Fix:**
1. Run `list` to see if any sessions exist
2. If sessions exist, run `resume <hash>` to activate one
3. If no sessions exist, run `init <path> -q "your query"` to create one

See also: [DS-306](ERROR-CODES.md#ds-306-session-not-found)

---

### "Forbidden pattern detected" / "Forbidden AST node"

**What you see:** `[ERROR] Forbidden pattern detected: __import__` or `[ERROR] Forbidden AST node: FunctionDef`

**Cause:** The REPL sandbox blocked your code. DeepScan uses a three-layer security model that restricts what can be executed.

**Common triggers:**

| You tried | Why it is blocked | Use instead |
|-----------|-------------------|-------------|
| `import os` | Module imports disabled | Use built-in helpers |
| `def my_func():` | Function definitions blocked | Use `lambda x: x` |
| `obj.__class__` | Dunder attributes blocked | Use `type(obj)` |
| `getattr(obj, 'x')` | Dynamic attribute access blocked | Use `obj.x` directly or `hasattr()` |
| `re.search(...)` | `re` module not available (CVE-2026-002) | Use `grep(pattern)` helper |
| `open('file.txt')` | File I/O blocked | Use `load_file('file.txt')` helper |
| `try: ... except:` | Exception handling blocked | Simplify the expression |

**Fix:** Use the built-in REPL helpers. For a complete list of what is allowed and blocked, see [Reference: REPL Sandbox](REFERENCE.md#repl-sandbox).

---

### "Active session already exists"

**What you see:** `[WARNING] Active session already exists: ...`

**Cause:** You tried to run `init` while a previous session is still active. This is overwrite protection.

**Fix:**
- Use `--force` to overwrite: `init <path> -q "query" --force`
- Resume the existing session: `resume`
- Delete the existing session: `abort <hash>`

---

### "Execution timed out" / DS-503

**What you see:** `TimeoutError` or `[DS-503] Timeout Error`

**Cause:** A REPL expression exceeded the time limit. Defaults: 5 seconds for simple commands, 30-120 seconds for `write_chunks` (auto-calculated from context size).

**Fix:** Use the `--timeout` flag for longer operations:
```bash
exec -c "paths = write_chunks(size=150000)" --timeout 60
```

For grep timeouts, simplify the regex pattern. Complex patterns trigger the 10-second ReDoS protection.

See also: [DS-503](ERROR-CODES.md#ds-503-timeout-error)

---

### "File too large" / DS-303

**What you see:** `[DS-303] File Too Large` or a file is silently skipped.

**Cause:** A single file exceeds the 10MB limit. Files over 10MB are automatically skipped during `init`.

**Fix:** Add large files to `.deepscanignore` to suppress warnings. If you need to analyze the file, split it first.

See also: [DS-303](ERROR-CODES.md#ds-303-file-too-large)

---

### "Context too large" / DS-304

**What you see:** `[DS-304] Context Too Large`

**Cause:** The total loaded context exceeds 50MB.

**Fix:**
1. Use `--lazy` mode to explore the structure first: `init <path> --lazy -q "query"`
2. Use `--target` to narrow to specific directories: `init <path> --target src/core --target src/api`
3. Add non-essential directories to `.deepscanignore`
4. Increase filtering with more ignore patterns

See also: [DS-304](ERROR-CODES.md#ds-304-context-too-large)

---

### "All results are placeholders"

**What you see:** All MAP results show placeholder data with no real findings.

**Cause:** The `map` command was run in CLI mode, not in the Claude Code environment. Real sub-agent processing requires Claude Code's Task tool.

**Fix:**
- Run `/deepscan map` inside Claude Code
- Or use `map --instructions` to get prompts, then execute them manually with the Task tool

See also: [Getting Started: Environment Note](GETTING-STARTED.md#environment-note)

---

### "LazyModeError"

**What you see:** `LazyModeError: This operation requires full context...`

**Cause:** You used a helper that needs full context (`peek`, `grep`, `chunk_indices`, `write_chunks`) while in lazy mode.

**Fix:** Use lazy-mode-compatible helpers instead:
- `peek()` -> `load_file('path/to/file.py')`
- `grep(pattern)` -> `grep_file(pattern, 'path/to/file.py')`
- To switch to full mode: `init <path> -q "query"` (without `--lazy`)

---

## How-To Workflows

### How to Cancel a Running Scan

**Single Ctrl+C (graceful):**
1. The current batch finishes processing
2. A checkpoint is saved
3. Resume instructions are printed:
```
[CANCEL] Cancellation requested, saving progress...
Resume this session:
  deepscan resume deepscan_1739700000_a1b2c3d4e5f6g7h8
```

**Double Ctrl+C (force quit):**
1. The process terminates immediately (exit code 130)
2. The in-progress batch is NOT saved
3. Previously completed batches are intact

The graceful shutdown has a 30-second timeout. If cleanup takes longer, the process force-quits automatically.

---

### How to Resume an Interrupted Scan

After a cancellation, crash, or network issue:

1. Find the session hash:
```bash
list
```

2. Resume the session:
```bash
resume <session_hash>
```
Or resume the most recent session:
```bash
resume
```

3. Continue processing:
```bash
map
```

The MAP phase automatically skips completed chunks and processes only the remaining ones.

---

### How to Scan Incrementally

Incremental scanning re-analyzes only files that changed since a previous scan.

1. Complete a full scan first and note the session hash:
```bash
init ./src -q "Security audit"
# ... complete the full workflow ...
export-results baseline.json
```

2. Make code changes.

3. Initialize an incremental scan:
```bash
init ./src -q "Security audit" --incremental --previous-session <hash_from_step_1>
```

4. The output shows what changed:
```
[Incremental] Changed/added files: 3
[Incremental] Deleted files: 1
```

5. Continue with the normal workflow (`write_chunks`, `map`, `reduce`). Only changed files are in the context.

> **Tip**: Install `xxhash` (`pip install xxhash`) for 3-5x faster file hashing on large codebases.

---

### How to Exclude Files (.deepscanignore)

Create a `.deepscanignore` file in your project root using gitignore-like syntax:

```
# Directories to skip (matched against directory names)
node_modules
vendor
dist
.cache

# File patterns (glob syntax)
*.min.js
*.map
*.lock
*.generated.*
data/fixtures/*.json
```

**Pattern types:**
- **Directory names** (no wildcards): matched against any path component
- **Glob patterns** (with `*` or `?`): matched against relative file paths
- Lines starting with `#` are comments
- Blank lines are ignored

DeepScan also auto-excludes these 19 directories by default: `node_modules`, `.git`, `.svn`, `.hg`, `__pycache__`, `.venv`, `venv`, `.env`, `env`, `.tox`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `dist`, `build`, `.next`, `.nuxt`, `target`, `vendor`.

---

### How to Use MAP Instructions Mode

For manual control over sub-agent execution:

1. Create chunks:
```bash
exec -c "paths = write_chunks(size=150000); print(f'{len(paths)} chunks')"
```

2. Generate sub-agent prompts:
```bash
map --instructions
```

3. Control pagination:
```bash
map --instructions --batch 2        # Show specific batch
map --instructions --limit 10       # More chunks per batch
map --instructions --output prompts.txt  # Save to file
```

4. Execute each prompt with the Claude Code Task tool.

5. Record results back:
```bash
exec -c 'add_result({"chunk_id": "a1b2c3d4", "status": "completed", "findings": [...], "missing_info": [], "partial_answer": null})'
```

6. Complete the workflow:
```bash
reduce
export-results results.json
```

---

### How to Uninstall DeepScan

1. Clean up all sessions:
```bash
poetry run python .claude/skills/deepscan/scripts/deepscan_engine.py clean --older-than 0
```

2. Remove cached data:
```bash
rm -rf ~/.claude/cache/deepscan/
```

3. Remove the plugin:
```bash
claude plugin remove deepscan
```

Or if installed via git clone:
```bash
rm -rf .claude/skills/deepscan/
rm -rf .claude-plugin/
```

4. Verify removal: trigger phrases like "analyze large codebase" should no longer activate DeepScan.

---

## Performance Troubleshooting

### Identifying the Slow Phase

Run `status` to see which phase the scan is in:

| Phase | If slow, likely cause | Fix |
|-------|-----------------------|-----|
| initialized | Large file loading | Use `--lazy` or `--target` to reduce scope |
| chunking | Semantic (tree-sitter) parsing | Use `write_chunks(semantic=False)` |
| mapping | Sub-agent API calls | Reduce chunk count with larger chunk sizes |
| reducing | Many findings to deduplicate | Normal; wait for completion |

### Monitoring Progress

```bash
# One-time check
progress

# Real-time monitoring (polls every 2 seconds)
progress --watch
```

### Reducing Chunk Count

More chunks means more API calls. DeepScan warns at 100 chunks and blocks at 500.

- Increase chunk size: `write_chunks(size=250000)`
- Use `--target` to narrow scope
- Add non-essential files to `.deepscanignore`

---

## Platform-Specific Issues

### Windows

**UnicodeEncodeError on output:**

Set the encoding environment variable:
```powershell
$env:PYTHONIOENCODING='utf-8'
```

DeepScan automatically reconfigures stdout/stderr encoding on Windows, but child processes may need this variable.

**No resource limits on Windows:**

The REPL sandbox's memory limits (256MB soft / 512MB hard), CPU limits (60s / 120s), and file size limits (10MB) rely on the Unix `resource` module, which is not available on Windows. The sandbox runs with degraded protection.

**Mitigation:** Run DeepScan inside a Docker container with `--memory` and `--cpus` flags for production use on Windows.

---

## See Also

- [Error Codes](ERROR-CODES.md) -- complete error code reference with all 31 DS-NNN codes
- [Reference](REFERENCE.md) -- full command, configuration, and REPL sandbox reference
- [Getting Started](GETTING-STARTED.md) -- step-by-step tutorial for first-time users
