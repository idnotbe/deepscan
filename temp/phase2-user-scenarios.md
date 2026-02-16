# Phase 2: User Scenarios with Detailed Workflows

> Generated: 2026-02-16
> Inputs: Phase 1 scenario ideas (32 scenarios), implementation analysis (17 modules), best practices research, doc restructuring plan
> Purpose: Grounded, step-by-step user scenarios that documentation must fully support

---

## How to Read This Document

Each scenario follows this structure:

| Field | Purpose |
|-------|---------|
| **Persona** | P1 (Beginner), P2 (Experienced), P3 (Security-focused) |
| **Context** | When/why this scenario arises |
| **Goal** | What the user wants to achieve |
| **Prerequisites** | What must be set up first |
| **Workflow** | Exact steps with commands and expected output |
| **Success Criteria** | How the user knows it worked |
| **Common Pitfalls** | What can go wrong and how to fix it |
| **Documentation Needed** | Which docs must cover this scenario |

Command prefix used throughout:

```bash
# Full CLI path (always works):
poetry run python .claude/skills/deepscan/scripts/deepscan_engine.py <command>

# In Claude Code (skill trigger):
/deepscan <command>
```

---

## Scenario 1: Installation and First-Time Setup

**Persona:** P1 (Beginner Developer)
**Context:** Developer discovers DeepScan through the Claude Code plugin directory or a colleague's recommendation. They want to install it and verify it works before analyzing any code.
**Goal:** Install the DeepScan plugin and confirm it is functional.

### Prerequisites

- Claude Code installed and working
- Python 3.10+ (the codebase uses `X | None` syntax which requires 3.10+)
- `poetry` installed (used to run the engine script)
- `pydantic` available (all state models depend on it)
- Optional: `tree-sitter-language-pack` for semantic chunking, `xxhash` for faster incremental hashing, `rich` for styled error output, `psutil` for memory-aware chunking

### Step-by-step Workflow

**Step 1: Install the plugin**

```bash
claude plugin add idnotbe/deepscan
```

Or clone manually:

```bash
git clone https://github.com/idnotbe/deepscan.git
# Copy .claude/ and .claude-plugin/ directories to your project
```

**Step 2: Verify installation**

```bash
poetry run python .claude/skills/deepscan/scripts/deepscan_engine.py --help
```

Expected output:

```
usage: deepscan_engine.py {init,status,exec,reset,export-results,list,resume,abort,clean,map,progress,reduce} ...
```

**Step 3: Verify Python dependencies**

```bash
python3 --version   # Must be 3.10+
poetry run python -c "import pydantic; print(pydantic.__version__)"
```

**Step 4: Verify plugin registration (in Claude Code)**

Type one of the trigger phrases in Claude Code:

```
analyze large codebase
```

Claude Code should recognize the DeepScan skill and begin the workflow.

### Success Criteria

- `--help` shows the command listing without import errors
- `pydantic` imports successfully
- Claude Code recognizes trigger phrases listed in SKILL.md frontmatter

### Common Pitfalls

| Problem | Cause | Fix |
|---------|-------|-----|
| `ModuleNotFoundError: pydantic` | Missing dependency | `pip install pydantic` or use `poetry install` |
| `SyntaxError` on startup | Python < 3.10 | Upgrade to Python 3.10+ |
| `ModuleNotFoundError: cancellation` | Running from wrong directory | Run from the repo root so Python can find sibling modules |
| Trigger phrases not recognized | Plugin not registered | Re-run `claude plugin add` or check `.claude-plugin/plugin.json` exists |
| Windows `UnicodeEncodeError` | Missing UTF-8 config | Set `$env:PYTHONIOENCODING='utf-8'` |

### Documentation Needed

- **README.md**: Prerequisites section, installation command, verification step
- **GETTING-STARTED.md**: Step 1 (installation with expected output)

---

## Scenario 2: Running a First Scan (Basic Usage)

**Persona:** P1 (Beginner Developer)
**Context:** The user has DeepScan installed and wants to analyze a small-to-medium project (10-100 source files) for the first time.
**Goal:** Complete an end-to-end scan from initialization through results.

### Prerequisites

- DeepScan installed (Scenario 1 completed)
- A project directory with source files to analyze
- Claude Code environment for the MAP phase (CLI produces placeholder results)

### Step-by-step Workflow

**Step 1: Initialize the scan**

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

**Step 2: Scout -- explore the loaded context**

```bash
exec -c "print(peek_head(3000))"
```

Expected output: First 3000 characters of the concatenated context, showing file headers like `--- FILE: src/app.py ---`.

```bash
exec -c "print(f'Context: {context_length()} chars')"
```

Expected output: `Context: 245832 chars`

```bash
exec -c "print(grep('TODO|FIXME', max_matches=10))"
```

Expected output: List of match dicts with `match`, `span`, and `snippet` keys.

**Step 3: Create chunks**

```bash
exec -c "paths = write_chunks(size=150000); print(f'{len(paths)} chunks created')"
```

Expected output:

```
[INFO] Using dynamic timeout: 30s for 245,832 bytes
2 chunks created
```

Chunks are written to `~/.claude/cache/deepscan/{session_hash}/chunks/`.

**Step 4: Run the MAP phase (Claude Code only)**

```bash
map
```

In CLI mode, you will see:

```
[WARN] Running in CLI-only mode. Sub-agents require Claude Code environment.
       Results will be placeholders. For real analysis, run in Claude Code
       or use 'map --instructions' to get prompts for manual processing.
[MAP] Processing batch 1/1 (2 chunks)
[MAP] Chunk 1/2: a1b2c3d4
[MAP] Chunk 2/2: e5f6g7h8
[MAP] Batch 1: 0 success, 2 placeholders, 0 failed
```

In Claude Code, actual sub-agents process each chunk and produce real findings.

**Step 5: Run the REDUCE phase**

```bash
reduce
```

Expected output (with real results):

```
[OK] Aggregation complete
  Total findings: 12
  Unique findings: 8
  Deduplication ratio: 33.3%
  Contradictions: 1
```

**Step 6: Export results**

```bash
export-results findings.json
```

Expected output:

```
[OK] Results exported to findings.json
```

The exported JSON contains:

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
      ],
      "missing_info": [],
      "partial_answer": null
    }
  ],
  "buffers": [],
  "final_answer": null
}
```

### Success Criteria

- `init` reports file count and total character size
- `peek_head` shows concatenated file content with `--- FILE: ... ---` headers
- `write_chunks` creates chunk files on disk
- `export-results` produces a valid JSON file with findings

### Common Pitfalls

| Problem | Cause | Fix |
|---------|-------|-----|
| "All results are placeholders" | MAP ran in CLI, not Claude Code | Run `/deepscan map` in Claude Code |
| `[ERROR] No active session` | Forgot to run `init` first | Run `init <path>` before other commands |
| No files found | Path is empty or all files filtered | Check path; check `.deepscanignore` |
| "Active session already exists" | Previous session not closed | Use `--force` flag or `resume` |
| Chunk count warning at 100 | Large codebase | Increase `chunk_size` or use `--target` to narrow scope |
| Chunk count blocked at 500 | Extremely large context | Use `--lazy` mode or split analysis |

### Documentation Needed

- **GETTING-STARTED.md**: Steps 2-7 (complete walkthrough with expected output)
- **SKILL.md**: Core Workflow section (already exists, verify accuracy)
- **TROUBLESHOOTING.md**: "All results are placeholders" entry

---

## Scenario 3: Understanding and Interpreting Scan Results

**Persona:** P1 (Beginner), P2 (Experienced)
**Context:** The user has completed a scan and has results (either from `reduce` output or `export-results`). They need to understand what the findings mean and how to act on them.
**Goal:** Interpret findings (point, evidence, confidence, location) and navigate to source code.

### Prerequisites

- A completed scan with at least some real (non-placeholder) results
- Exported JSON file or access to the reduce summary

### Step-by-step Workflow

**Step 1: Check current status**

```bash
status
```

Expected output:

```
=== DeepScan Status ===
Session:  deepscan_1739700000_a1b2c3d4e5f6g7h8
Phase:    reduce
Context:  245,832 chars
Chunks:   2 total, 2 processed
Progress: 100.0%
Buffers:  0
```

Phase should be "reduce" or "completed". If phase is still "mapping", not all chunks are processed.

**Step 2: View the reduce summary**

```bash
reduce
```

The summary shows:
- **Total findings**: All findings across all chunks before deduplication
- **Unique findings**: After deduplication (Jaccard similarity threshold 0.7)
- **Deduplication ratio**: Percentage of duplicates removed
- **Contradictions**: Findings where sub-agents disagreed (detected via negation heuristic)

**Step 3: Export and examine findings**

```bash
export-results findings.json
```

Each finding in the JSON has these fields:

| Field | Type | Meaning |
|-------|------|---------|
| `point` | string | What was found (the main claim) |
| `evidence` | string | Supporting code/text evidence |
| `confidence` | "high" / "medium" / "low" | Sub-agent's confidence level |
| `location` | `{"file": "...", "line": N}` or `{"context": "..."}` | Where in the source code |
| `verification_required` | boolean | Whether human review is needed (NEEDS_VERIFICATION prefix) |

**Step 4: Navigate to source code**

From a finding like:
```json
{
  "point": "Hardcoded database password",
  "evidence": "Line 12: DB_PASS = 'admin123'",
  "confidence": "high",
  "location": {"file": "src/config.py", "line": 12}
}
```

Open `src/config.py` at line 12 to verify the finding.

**Step 5: Understand confidence levels**

| Confidence | Meaning | Action |
|------------|---------|--------|
| `high` | Strong evidence, clear pattern match | Fix immediately |
| `medium` | Plausible but context-dependent | Review and decide |
| `low` | Speculative or incomplete evidence | Investigate further |

**Step 6: Handle contradictions**

If contradictions are reported, the reduce output lists them. Contradictions occur when two sub-agents make opposing claims about the same code (detected via negation words: "no ", "not ", "never ", "without ", "n't "). Review both findings manually.

### Success Criteria

- User can map each finding to a specific source file and line
- User understands confidence levels and prioritizes accordingly
- Contradictions are reviewed and resolved manually

### Common Pitfalls

| Problem | Cause | Fix |
|---------|-------|-----|
| All findings show `confidence: "medium"` | Default when sub-agent doesn't specify | Review evidence to judge actual severity |
| `location` field is null or missing | Sub-agent didn't extract location | Use `evidence` field text to find the code |
| Findings reference deleted files | Ghost findings from incremental scan | Re-run reduce (P7-003 ghost cleanup filters these) |
| Duplicate-looking findings remain | Similarity below 0.7 threshold | Review manually; adjust threshold if needed |

### Documentation Needed

- **GETTING-STARTED.md**: Step 6 (interpreting findings with example output)
- **README.md**: Example finding in the Usage section
- **ARCHITECTURE.md**: Section 3.5 (deduplication and contradiction detection -- already exists)

---

## Scenario 4: Configuring Scan Parameters

**Persona:** P2 (Experienced Developer)
**Context:** The user has run a basic scan and wants to optimize it for their specific codebase. They need to understand available configuration options.
**Goal:** Configure chunk size, agent type, adaptive chunking, and ignore patterns.

### Prerequisites

- DeepScan installed and a successful first scan completed
- Understanding of what chunks are (from Scenario 2)

### Step-by-step Workflow

**Step 1: Choose an agent type**

Available types (from `subagent_prompt.py` SUPPORTED_AGENT_TYPES):

| Type | Flag | Best For |
|------|------|----------|
| `general` | `--agent-type general` | Broad code review (default) |
| `security` | `--agent-type security` | Vulnerability hunting, credential leaks, injection flaws |
| `architecture` | `--agent-type architecture` | Design patterns, coupling, dependency analysis |
| `performance` | `--agent-type performance` | Bottlenecks, N+1 queries, algorithmic complexity |

```bash
init ./src -q "Find SQL injection and XSS vulnerabilities" --agent-type security
```

**Step 2: Adjust chunk size**

Default is 150,000 characters. Valid range: 50,000 - 300,000.

```bash
# For dense code (many small files): smaller chunks, more granularity
exec -c "paths = write_chunks(size=100000); print(f'{len(paths)} chunks')"

# For sparse code (large files, docs): larger chunks, fewer API calls
exec -c "paths = write_chunks(size=250000); print(f'{len(paths)} chunks')"
```

The `chunk_indices` helper lets you preview without writing:

```bash
exec -c "indices = chunk_indices(size=100000); print(f'{len(indices)} chunks would be created')"
```

Chunk size limits (enforced in `helpers.py`):
- Minimum: 50,000 characters
- Maximum: 300,000 characters
- Overlap maximum: 50,000 characters (must be less than chunk size)

**Step 3: Enable adaptive chunking**

Adaptive mode auto-detects content type from file extensions and uses optimized chunk sizes (from `constants.py` CHUNK_SIZE_BY_EXTENSION):

| Content Type | Extensions | Chunk Size |
|-------------|------------|------------|
| Code | `.py`, `.js`, `.ts`, `.java`, `.go`, etc. | 100,000 |
| Config | `.json`, `.yaml`, `.yml`, `.toml` | 80,000 |
| Docs (markup) | `.md`, `.rst`, `.html` | 150,000 - 200,000 |
| Docs (text) | `.txt` | 250,000 |

```bash
init ./src -q "Review code quality" --adaptive
```

Expected output includes:

```
  [Adaptive] Content type: code:.py
  [Adaptive] Chunk size: 100,000 characters
```

**Step 4: Create a .deepscanignore file**

Create `.deepscanignore` in the project root (gitignore-like syntax):

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
```

Default ignored directories (from `walker.py` DEFAULT_PRUNE_DIRS): `node_modules`, `.git`, `.svn`, `.hg`, `__pycache__`, `.venv`, `venv`, `.env`, `env`, `.tox`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `dist`, `build`, `.next`, `.nuxt`, `target`, `vendor`.

**Step 5: Use semantic chunking**

If `tree-sitter-language-pack` is installed, semantic chunking splits code at class/function boundaries instead of raw character offsets. Supported languages: Python, JavaScript, TypeScript, Java, Go.

```bash
exec -c "paths = write_chunks(size=150000, semantic=True); print(f'{len(paths)} chunks')"
```

### Success Criteria

- Agent type is shown in init output when non-default
- Adaptive chunking reports detected content type
- `.deepscanignore` patterns are respected (excluded files don't appear in context)
- Semantic chunks align with function/class boundaries

### Common Pitfalls

| Problem | Cause | Fix |
|---------|-------|-----|
| `[ERROR] Invalid Chunk Size` (DS-004) | Size outside 50K-300K range | Use a value between 50000 and 300000 |
| `[ERROR] Overlap Exceeds Size` (DS-005) | Overlap >= chunk_size | Set overlap to less than chunk_size |
| `.deepscanignore` not working | File in wrong directory | Place it in the project root being scanned |
| Semantic chunking falls back to text | tree-sitter not installed | `pip install tree-sitter-language-pack` |
| `RuntimeWarning: tree_sitter import failed` | Package not available | Install tree-sitter or use text-based chunking |

### Documentation Needed

- **REFERENCE.md**: Configuration Settings table, Specialized Agent Types table, .deepscanignore format
- **USE_CASES.md**: Section 3 (chunking strategies -- already exists, verify accuracy)
- **SKILL.md**: Configuration table (already exists)

---

## Scenario 5: Using Incremental Scanning

**Persona:** P2 (Experienced Developer)
**Context:** The user has completed a full scan and made code changes. They want to re-analyze only the changed files instead of re-scanning the entire codebase.
**Goal:** Run an incremental scan that processes only changed/added files, achieving 3-10x speedup.

### Prerequisites

- A completed previous scan with a known session hash
- Code changes made since the previous scan
- Optional: `xxhash` package for faster file hashing (falls back to SHA-256)

### Step-by-step Workflow

**Step 1: Find the previous session hash**

```bash
list
```

Expected output:

```
=== DeepScan Sessions (2) ===

Hash                                          Phase        Progress   Modified
------------------------------------------------------------------------------------------
deepscan_1739700000_a1b2c3d4e5f6g7h8          completed    100.0%     2026-02-15 14:30
deepscan_1739600000_x9y8z7w6v5u4t3s2          completed    100.0%     2026-02-14 10:15

(Current: deepscan_1739700000_a1b2c3d4e5f6g7h8)
```

Copy the session hash you want to use as the baseline.

**Step 2: Make code changes**

Edit, add, or delete source files in your project.

**Step 3: Initialize incremental scan**

```bash
init ./src -q "Find security vulnerabilities" \
    --incremental \
    --previous-session deepscan_1739700000_a1b2c3d4e5f6g7h8
```

Expected output:

```
[OK] DeepScan initialized
  Session: deepscan_1739800000_newSessionHash
  Context: /home/user/project/src
  Size: 247,100 characters
  Files: 48
  [Incremental] Enabled
  [Incremental] Previous session: deepscan_173970...
  [Incremental] Changed/added files: 3
  [Incremental] Deleted files: 1
```

If no changes were detected:

```
  [Incremental] Changed/added files: 0
  [Incremental] Deleted files: 0
  [Incremental] No changes detected - analysis can be skipped!
```

**Step 4: Proceed with the normal workflow**

Only changed/added files are included in the context, so chunking and MAP are faster:

```bash
exec -c "paths = write_chunks(size=150000); print(f'{len(paths)} chunks')"
# Fewer chunks than the full scan

map
reduce
export-results incremental-findings.json
```

**Step 5: Understand delta detection**

The `incremental.py` module uses `FileHashManifest` to:
1. Hash all files in the current directory (using xxHash3 if available, SHA-256 otherwise)
2. Compare against the previous session's manifest
3. Produce a `FileDelta` with `changed_files`, `added_files`, `deleted_files`
4. During reduce, ghost findings from deleted files are filtered out (P7-003)

### Success Criteria

- Init output shows incremental stats (changed/added/deleted counts)
- Fewer chunks are created compared to a full scan
- Ghost findings from deleted files are filtered during reduce

### Common Pitfalls

| Problem | Cause | Fix |
|---------|-------|-----|
| "No changes detected" when changes exist | Wrong previous-session hash | Use `list` to find the correct hash |
| Previous session not found | Session was cleaned/aborted | Run a full scan first |
| Slow hashing on large codebases | xxhash not installed | `pip install xxhash` for 3-5x faster hashing |
| Ghost findings in results | Reduce not run after incremental scan | Always run `reduce` to trigger ghost cleanup |

### Documentation Needed

- **TROUBLESHOOTING.md**: "How to Scan Incrementally" workflow section
- **REFERENCE.md**: `--incremental` and `--previous-session` flags
- **USE_CASES.md**: Section 8 (incremental analysis -- exists, enhance with step-by-step)

---

## Scenario 6: Checkpoint and Resume a Long Scan

**Persona:** P1 (Beginner), P2 (Experienced)
**Context:** A scan on a large codebase is interrupted -- either intentionally (Ctrl+C), by a crash, or by a network issue. The user wants to resume without losing progress.
**Goal:** Resume an interrupted scan from the last checkpoint.

### Prerequisites

- An active or interrupted scan session
- Understanding that checkpoints save after each MAP batch

### Step-by-step Workflow

**Step 1: Interrupt a running scan (intentional)**

During a MAP phase:

- **First Ctrl+C (graceful)**: Saves the current batch checkpoint and exits cleanly.

```
^C
[CANCEL] Cancellation requested, saving progress...
[MAP] Batch 3: 4 success, 0 placeholders, 1 failed
[CANCEL] Cancellation requested after batch, saving progress...

Resume this session:
  deepscan resume deepscan_1739700000_a1b2c3d4e5f6g7h8
```

- **Second Ctrl+C (force quit)**: Kills the process immediately (exit code 130). In-progress chunks are not saved, but previously completed batches are safe.

**Step 2: Check available sessions**

```bash
list
```

Find the interrupted session. Its phase will show "map" and progress will be < 100%.

**Step 3: Resume the session**

```bash
resume deepscan_1739700000_a1b2c3d4e5f6g7h8
```

Expected output:

```
[OK] Resumed session: deepscan_1739700000_a1b2c3d4e5f6g7h8
  Phase: map
  Progress: 60.0%
  Chunks: 10 total, 6 processed
  Checkpoint: batch 3 (2026-02-15 14:30)
```

Or resume the most recent session:

```bash
resume
```

Expected output:

```
Resuming most recent session: deepscan_1739700000_a1b2c3d4e5f6g7h8
[OK] Resumed session: ...
```

**Step 4: Continue processing**

```bash
map
```

The MAP phase skips already-completed chunks (those with status not in "placeholder" or "pending") and processes remaining ones.

**Step 5: Complete the workflow**

```bash
reduce
export-results results.json
```

### Success Criteria

- Graceful Ctrl+C shows resume instructions with the session hash
- `resume` restores the session with correct progress percentage
- `map` after resume only processes remaining chunks, not all chunks
- Previously completed chunks retain their results

### Common Pitfalls

| Problem | Cause | Fix |
|---------|-------|-----|
| "No sessions to resume" | All sessions were cleaned or aborted | Run a fresh `init` |
| Resume shows 0% progress | Checkpoint from a crash before any batch completed | Re-run `map` from the beginning |
| Duplicate findings after resume | Placeholder results not cleared | `map` handles idempotent updates (replaces existing results per chunk) |
| `[ERROR] Invalid session hash format` | Hash contains invalid characters | Copy the exact hash from `list` output |
| Force quit lost progress | Double Ctrl+C before checkpoint saved | Only the in-progress batch is lost; completed batches are safe |

### Documentation Needed

- **TROUBLESHOOTING.md**: "How to Resume an Interrupted Scan" and "How to Cancel a Running Scan"
- **GETTING-STARTED.md**: Brief mention of resume capability
- **REFERENCE.md**: `resume` and `abort` command reference

---

## Scenario 7: Using the REPL Sandbox

**Persona:** P1 (Beginner), P2 (Experienced)
**Context:** The user wants to interactively explore loaded context using the sandboxed REPL. They need to know what operations are allowed and what is blocked.
**Goal:** Use REPL helpers and custom Python expressions to analyze loaded context safely.

### Prerequisites

- An initialized session with context loaded (`init` completed)
- Understanding that the REPL runs in a security sandbox

### Step-by-step Workflow

**Step 1: Use built-in helpers for exploration**

```bash
# View first 5000 characters of context
exec -c "print(peek_head(5000))"

# View last 3000 characters
exec -c "print(peek_tail(3000))"

# View a specific range
exec -c "print(peek(10000, 15000))"

# Check total size
exec -c "print(context_length())"

# Search with regex (ReDoS-protected)
exec -c "results = grep('password|secret|key', max_matches=20); print(results)"

# Search a specific file
exec -c "results = grep_file('TODO', 'src/app.py'); print(results)"
```

**Step 2: Use collection operations**

```bash
# Count lines in context
exec -c "print(len(content.split('\\n')))"

# Find all file headers
exec -c "lines = [l for l in content.split('\\n') if l.startswith('--- FILE:')]; print('\\n'.join(lines))"

# Filter findings by confidence
exec -c "status = get_status(); print(status)"
```

**Step 3: Use write/state helpers**

```bash
# Record a manual finding
exec -c 'add_result({"chunk_id": "manual_01", "status": "completed", "findings": [{"point": "Found hardcoded API key", "evidence": "Line 12: API_KEY = abc123", "confidence": "high"}], "missing_info": [], "partial_answer": None})'

# Add notes to buffer
exec -c "add_buffer('Need to review auth module more carefully')"

# Check buffers
exec -c "print(get_buffers())"

# Set phase manually
exec -c "set_phase('mapping')"
```

**Step 4: Know what's allowed**

Safe builtins available (35 total, from `constants.py` SAFE_BUILTINS):
`len`, `str`, `int`, `float`, `bool`, `list`, `dict`, `tuple`, `set`, `print`, `range`, `enumerate`, `zip`, `map`, `filter`, `min`, `max`, `sum`, `sorted`, `reversed`, `abs`, `round`, `isinstance`, `type`, `repr`, `True`, `False`, `None`, `all`, `any`, `slice`, `dir`, `vars`, `hasattr`, `callable`, `id`

Allowed syntax:
- Arithmetic, comparisons, boolean logic
- String operations (`.upper()`, `.split()`, f-strings)
- Collection operations (list/dict/set/tuple creation and methods)
- Comprehensions: `[x for x in data]`, `{k: v for ...}`, `{x for x in data}`
- Lambda expressions: `lambda x: x > 0`
- Ternary: `x if condition else y`
- Variable assignment: `x = 5`, `x += 1`
- For loops and if statements
- Keyword arguments: `func(key=value)`

**Step 5: Know what's blocked (and why)**

| Blocked Operation | Example | Error Message | Security Reason |
|-------------------|---------|---------------|-----------------|
| Imports | `import os` | "Forbidden AST node: Import" | System access |
| `__import__` | `__import__('os')` | "Forbidden pattern detected: `__import__`" | Bypass import blocking |
| `exec`/`eval`/`compile` | `exec('code')` | "Forbidden pattern detected: `exec\\s*\\(`" | Arbitrary code execution |
| `open` | `open('file.txt')` | "Forbidden pattern detected: `open\\s*\\(`" | Filesystem access |
| `os.*` | `os.system('cmd')` | "Forbidden pattern detected: `os\\.`" | OS-level access |
| `subprocess` | `subprocess.run(...)` | "Forbidden pattern detected: `subprocess`" | Process spawning |
| `sys.*` | `sys.exit()` | "Forbidden pattern detected: `sys\\.`" | System manipulation |
| `getattr`/`setattr` | `getattr(obj, 'x')` | "Forbidden pattern detected: `getattr\\s*\\(`" | AST bypass |
| Dunder attributes | `obj.__class__` | "Forbidden attribute: `__class__`" | Sandbox escape |
| Any `_`-prefixed attr | `obj._private` | "Forbidden attribute: `_private`" | Internal access |
| Function/class defs | `def foo(): pass` | "Forbidden AST node: FunctionDef" | Hidden complexity |
| Try/raise/with | `try: ...` | "Forbidden AST node: Try" | Exception control flow |
| Yield/async | `yield x` | "Forbidden AST node: Yield" | Generator/async abuse |

### Success Criteria

- Helper functions return expected data types
- Comprehensions and lambda expressions work
- Forbidden patterns produce clear error messages identifying the blocked pattern
- `add_result` successfully records findings

### Common Pitfalls

| Problem | Cause | Fix |
|---------|-------|-----|
| "Forbidden pattern detected" | Used a blocked function name | Use the equivalent helper (e.g., `grep()` instead of `re.search()`) |
| "Forbidden AST node: FunctionDef" | Tried to define a function | Use lambda or inline expressions |
| "Forbidden attribute: _private" | Accessed underscore-prefixed attribute | Avoid private attributes; use public API |
| `LazyModeError` | Used `peek`/`grep`/`chunk_indices` in lazy mode | Use `load_file()`, `get_tree_view()`, or `grep_file()` instead |
| Timeout (5 seconds default) | Expression too slow | Use `--timeout N` flag for longer operations |
| Code truncated at 100KB | Input code exceeds MAX_CODE_LENGTH | Simplify the expression |

### Documentation Needed

- **REFERENCE.md**: REPL Sandbox section (allowed/blocked tables), Helper Functions table
- **TROUBLESHOOTING.md**: "Forbidden pattern" and "Forbidden AST node" error entries
- **GETTING-STARTED.md**: Step 3 (basic scout examples)
- **SECURITY.md**: "Security at a Glance" summary for non-experts

---

## Scenario 8: Handling Errors (with Specific Error Codes)

**Persona:** P1 (Beginner), P2 (Experienced)
**Context:** The user encounters an error during any phase of the workflow. They see an error message with a DS-NNN code and need to understand what went wrong and how to fix it.
**Goal:** Diagnose and resolve errors using error codes and remediation hints.

### Prerequisites

- Any DeepScan operation that produced an error
- Understanding of the error code format: `[DS-NNN] Title: message`

### Step-by-step Workflow

**Step 1: Read the error message**

Error messages follow this format:

```
[DS-306] Session Not Found: No active session found
  Suggestion: Use 'deepscan list' to see available sessions. Session: <session_id>
```

The components:
- `DS-306`: Error code (lookup in ERROR-CODES.md)
- `Session Not Found`: Error title
- `No active session found`: Specific message
- `Suggestion:`: Remediation hint

**Step 2: Understand error categories**

| Code Range | Category | Exit Code | Meaning |
|------------|----------|-----------|---------|
| DS-0xx | Validation | 2 | Invalid input (bad path, bad chunk size) |
| DS-1xx | Parsing | 3 | Failed to parse code, JSON, or checkpoint |
| DS-2xx | Chunking | 4 | Chunk creation or aggregation problems |
| DS-3xx | Resource | 5 | File not found, permission denied, too large |
| DS-4xx | Config | 6 | Configuration errors |
| DS-5xx | System | 1 (or 130) | Internal errors, timeouts, cancellation |

**Step 3: Apply common fixes**

Top 8 errors and their fixes:

| Error | Quick Fix |
|-------|-----------|
| **DS-001** Invalid Context Path | Verify the path exists: `ls <path>` |
| **DS-004** Invalid Chunk Size | Use a value between 50,000 and 300,000 |
| **DS-006** Empty Context | Check path has analyzable files; check `.deepscanignore` |
| **DS-303** File Too Large | Files >10MB are auto-skipped; use `.deepscanignore` to exclude explicitly |
| **DS-304** Context Too Large | Total >50MB; use `--lazy` or `--target` to reduce scope |
| **DS-306** Session Not Found | Run `list` to find sessions; run `init` to create one |
| **DS-503** Timeout | Use `--timeout N` flag or reduce chunk size |
| **DS-505** Cancelled By User | Resume with `resume <session_hash>` |

**Step 4: Use verbose mode for more detail**

When Rich is installed, errors include styled output with file paths, categories, and documentation URLs. The `handle_error` function in `error_codes.py` supports a verbose mode that shows cause chains.

**Step 5: Check exit codes for automation**

```bash
poetry run python .claude/skills/deepscan/scripts/deepscan_engine.py init /nonexistent
echo $?  # Returns 5 (Resource error)
```

### Success Criteria

- User can map error code to category and understand severity
- Remediation hint provides actionable fix
- Exit codes are consistent with Unix conventions

### Common Pitfalls

| Problem | Cause | Fix |
|---------|-------|-----|
| No error code shown | Unstructured exception (not a DeepScanError) | Report as a bug; check stderr for Python traceback |
| Remediation says `<file_path>` | Context not available for template | The hint is generic; check the error message for specifics |

### Documentation Needed

- **ERROR-CODES.md**: Complete reference for all 26 error codes with remediation
- **TROUBLESHOOTING.md**: Top errors organized by symptom
- **SKILL.md**: Link to ERROR-CODES.md from troubleshooting section

---

## Scenario 9: Cancellation and Graceful Shutdown

**Persona:** P1 (Beginner), P2 (Experienced)
**Context:** The user started a scan with wrong parameters, the scan is taking too long, or they need to stop for any reason. They want to cancel without losing completed work.
**Goal:** Cancel a running scan gracefully and optionally resume later.

### Prerequisites

- A scan in progress (typically during MAP phase)

### Step-by-step Workflow

**Step 1: Graceful cancel (single Ctrl+C)**

Press Ctrl+C once during any operation. The cancellation manager (`cancellation.py`) handles the signal:

1. Current batch completes processing
2. Checkpoint is saved with batch index and completed chunks
3. State is persisted to disk
4. Resume instructions are printed:

```
[CANCEL] Cancellation requested, saving progress...

Resume this session:
  deepscan resume deepscan_1739700000_a1b2c3d4e5f6g7h8
```

The graceful shutdown has a 10-second timeout (configurable via `graceful_timeout`). If cleanup takes longer than 10 seconds, the process force-quits.

**Step 2: Force quit (double Ctrl+C)**

Press Ctrl+C twice quickly. The second signal triggers immediate termination via `os._exit(130)`. This:
- Skips remaining cleanup
- Does NOT save the in-progress batch
- Previously saved checkpoints are still intact
- Exit code is 130 (128 + SIGINT, Unix convention)

**Step 3: Resume after cancellation**

```bash
resume deepscan_1739700000_a1b2c3d4e5f6g7h8
```

Then continue:

```bash
map
```

The MAP phase automatically skips completed chunks and processes only remaining ones.

**Step 4: Abort instead of resume**

If you don't want to resume:

```bash
abort deepscan_1739700000_a1b2c3d4e5f6g7h8
```

This permanently deletes the session directory (including all checkpoints, chunks, and results).

### Success Criteria

- Single Ctrl+C saves progress and shows resume instructions
- Double Ctrl+C exits immediately with code 130
- Resume after cancel correctly skips completed chunks
- Abort permanently removes the session

### Common Pitfalls

| Problem | Cause | Fix |
|---------|-------|-----|
| No resume instructions shown | Force quit happened too fast | Check `list` for the session hash |
| Checkpoint shows batch -1 | Final cancellation save (expected) | Resume normally; it works correctly |
| Process hangs after Ctrl+C | Graceful cleanup taking long | Wait up to 10 seconds, or press Ctrl+C again to force quit |

### Documentation Needed

- **TROUBLESHOOTING.md**: "How to Cancel a Running Scan" and "How to Resume an Interrupted Scan"
- **ERROR-CODES.md**: DS-505 entry with exit code 130
- **REFERENCE.md**: `resume` and `abort` commands

---

## Scenario 10: Security -- Understanding Sandbox Restrictions

**Persona:** P3 (Security-Conscious Developer), P1 (Beginner)
**Context:** The user is evaluating DeepScan for use on sensitive code and wants to understand the security model. Or a beginner keeps hitting "Forbidden pattern" errors and wants to understand why.
**Goal:** Understand the three-layer sandbox model and what is/isn't safe.

### Prerequisites

- Basic understanding of Python and code execution concepts
- For P3: interest in the threat model and defense-in-depth architecture

### Step-by-step Workflow

**Step 1: Understand the three security layers**

The REPL sandbox in `deepscan_engine.py` (lines 344-462) enforces three independent layers:

| Layer | What It Checks | How It Works | Bypass Difficulty |
|-------|---------------|--------------|-------------------|
| **1. Forbidden Patterns** | String-level regex scan | 14 patterns block `__import__`, `exec(`, `eval(`, `open(`, `os.`, `subprocess`, `sys.`, etc. | Cannot bypass with code tricks |
| **2. AST Whitelist** | Parsed syntax tree | Only ~50 explicitly allowed AST node types; everything else is blocked | Cannot bypass without valid Python syntax |
| **3. Attribute Blocking** | Attribute access inspection | All `_`-prefixed attributes blocked + 20 specific dunder attrs (`__class__`, `__globals__`, etc.) | Blocks introspection chains |

Each layer is independent: code must pass ALL three to execute.

**Step 2: Understand execution isolation**

The `repl_executor.py` module provides additional protection:

| Protection | Mechanism | Details |
|------------|-----------|---------|
| Process isolation | `SafeREPLExecutor` runs code in a daemon subprocess | Crash in user code doesn't crash the host |
| Timeout | 5-second default, configurable | Prevents infinite loops |
| Memory limit (Unix) | 256MB soft / 512MB hard via `resource` module | Prevents memory bombs |
| CPU limit (Unix) | 60s soft / 120s hard | Prevents CPU monopolization |
| File size limit (Unix) | 10MB max per file write | Prevents disk fills |
| Namespace restriction | Only SAFE_BUILTINS + helpers in scope | No access to full Python stdlib |

**Step 3: Understand what's NOT protected (known limitations)**

| Limitation | Risk | Mitigation |
|------------|------|------------|
| No `resource` module on Windows | Memory/CPU limits not enforced | Run in a container with `--memory` flag |
| Zombie threads | Thread-based timeout can't kill hanging threads | Threads may consume resources until process exit |
| Introspection primitives | `type`, `vars`, `dir`, `hasattr` are available | These are needed for analysis; monitored for escape chains |
| No HMAC on state files | State files could be tampered with | State files are in user's home directory (trusted perimeter) |

**Step 4: Test the sandbox boundaries**

```bash
# This will be blocked by Layer 1 (forbidden pattern):
exec -c "import os"
# Output: [ERROR] Forbidden AST node: Import

exec -c "__import__('os')"
# Output: [ERROR] Forbidden pattern detected: __import__

# This will be blocked by Layer 2 (AST whitelist):
exec -c "def evil(): pass"
# Output: [ERROR] Forbidden AST node: FunctionDef

# This will be blocked by Layer 3 (attribute blocking):
exec -c "x = 'hello'; print(x.__class__)"
# Output: [ERROR] Forbidden attribute: __class__

# This works (safe operations):
exec -c "data = [1,2,3]; print(sorted(data, reverse=True))"
# Output: [3, 2, 1]
```

**Step 5: Understand path traversal protection**

Four modules enforce path containment:

| Module | Protection |
|--------|-----------|
| `state_manager.py` | `_safe_write()` uses `resolve().relative_to()` to ensure writes stay in cache dir |
| `ast_chunker.py` | `resolve(strict=True) + relative_to()` ensures files are within project root |
| `helpers.py` | `write_chunks`, `load_file`, `preview_dir` all validate paths against project root |
| `walker.py` | `follow_symlinks=False` throughout; symlinks are never followed |

### Success Criteria

- User understands the three-layer model and what each layer blocks
- User knows the known limitations and platform-specific caveats
- Security-focused users can evaluate the sandbox for enterprise use

### Common Pitfalls

| Problem | Cause | Fix |
|---------|-------|-----|
| "But I need `getattr`" | Legitimate introspection need | Use `dir()`, `vars()`, or `hasattr()` instead |
| "Why can't I define functions?" | FunctionDef blocked by AST whitelist | Use lambda for simple functions: `lambda x: x > 0` |
| Windows feels less secure | `resource` module unavailable | Run DeepScan in a Docker container with memory limits |

### Documentation Needed

- **SECURITY.md**: "Security at a Glance" summary (new section at top), known limitations with mitigations
- **REFERENCE.md**: REPL Sandbox section (allowed/blocked tables)
- **TROUBLESHOOTING.md**: "Forbidden pattern" and "Forbidden AST node" entries

---

## Scenario 11: Large Codebase Handling Strategies

**Persona:** P2 (Experienced Developer)
**Context:** The user has a large codebase (500+ files, >50MB total) that exceeds DeepScan's default limits. They need strategies to analyze it effectively.
**Goal:** Successfully analyze a large codebase by using lazy mode, targeted scanning, or splitting the analysis.

### Prerequisites

- DeepScan installed
- A large codebase that exceeds the 50MB total context limit (DS-304)

### Step-by-step Workflow

**Step 1: Try lazy mode for initial exploration**

Lazy mode loads only the directory structure (no file contents), allowing you to identify areas of interest:

```bash
init ./large-project --lazy -q "Architecture review" --depth 4
```

Expected output:

```
[OK] DeepScan initialized
  Session: deepscan_1739700000_abcdef1234567890
  Context: /home/user/large-project
  Size: 0 characters
  Files: 0
  [Mode] LAZY
  [Mode] Max depth: 4
  [Mode] File limit: 50

============================================================
  Lazy Mode Active (--lazy)
   Structure only. File contents not loaded.
============================================================

large-project/
|--- src/
|    |--- api/
|    |    |--- routes.py (12.3 KB)
|    |    |--- middleware.py (8.1 KB)
|    |--- core/
|    |    |--- engine.py (45.2 KB)
...

------------------------------------------------------------
  Next Steps:
  * View specific file: deepscan exec -c "load_file('path/to/file.py')"
  * Preview subdirectory: deepscan exec -c "preview_dir('subdir')"
  * Check mode: deepscan exec -c "is_lazy_mode()"
  * Full scan: deepscan init /home/user/large-project (no --lazy)
------------------------------------------------------------
```

**Step 2: Explore with lazy mode helpers**

```bash
# Preview a specific subdirectory
exec -c "print(preview_dir('src/api', max_depth=2, max_files=30))"

# Load a specific file for inspection
exec -c "content = load_file('src/core/engine.py'); print(content[:3000])"

# Search within a specific file (works in lazy mode)
exec -c "print(grep_file('vulnerability', 'src/core/engine.py'))"

# Get the tree view
exec -c "print(get_tree_view())"
```

**Step 3: Use targeted mode for focused analysis**

After identifying areas of interest, use targeted mode:

```bash
init ./large-project -q "Security audit of API layer" \
    --target src/api \
    --target src/auth \
    --target src/middleware
```

The `--target` flag can be repeated. Only specified paths are loaded into context.

**Step 4: Split the analysis into multiple sessions**

For very large codebases, analyze in stages:

```bash
# Stage 1: API layer
init ./project --target src/api -q "Security audit" --agent-type security
# Complete the full workflow (chunk, map, reduce, export)
export-results api-findings.json

# Stage 2: Core logic
init ./project --target src/core -q "Security audit" --agent-type security --force
export-results core-findings.json

# Stage 3: Data layer
init ./project --target src/data -q "Security audit" --agent-type security --force
export-results data-findings.json
```

**Step 5: Optimize with .deepscanignore**

Exclude non-essential files to reduce context size:

```
# Generated/vendored code
vendor/
generated/
*.min.js
*.bundle.js

# Test fixtures and data
test/fixtures/
*.snapshot

# Large binary-adjacent files
*.sql.gz
*.csv
```

### Success Criteria

- Lazy mode loads quickly with a tree view (no file content)
- Targeted mode loads only specified paths within the 50MB limit
- Split analysis produces separate result files that can be reviewed individually
- `.deepscanignore` reduces context size enough to fit limits

### Common Pitfalls

| Problem | Cause | Fix |
|---------|-------|-----|
| `LazyModeError` on `peek()` | `peek` needs full context | Use `load_file()` or `grep_file()` in lazy mode |
| `[ERROR] Context Too Large` (DS-304) | Still over 50MB with targets | Narrow targets further or use `.deepscanignore` |
| "Active session already exists" | Forgot `--force` between stages | Use `--force` or `abort` the previous session |
| Binary file loaded | No automatic binary detection during init | Add binary extensions to `.deepscanignore` |

### Documentation Needed

- **USE_CASES.md**: Section 1 (lazy and targeted modes -- already exists, verify)
- **TROUBLESHOOTING.md**: DS-304 error entry with strategies
- **REFERENCE.md**: `--lazy`, `--target`, `--depth` flag reference

---

## Scenario 12: Customizing Scan Agents (--agent-type)

**Persona:** P2 (Experienced Developer)
**Context:** The user wants to run a specialized analysis rather than a general code review. They've heard about the four agent types but aren't sure which to choose.
**Goal:** Select and use the right specialized agent type for their analysis goal.

### Prerequisites

- DeepScan installed
- A project to analyze
- Claude Code environment for real sub-agent processing

### Step-by-step Workflow

**Step 1: Understand agent types**

Each agent type provides specialized system instructions to sub-agents (defined in `subagent_prompt.py` AGENT_TYPE_INSTRUCTIONS):

| Agent Type | System Instruction Focus | Verification Rules | Best Query Examples |
|------------|-------------------------|-------------------|---------------------|
| `general` | Broad analysis: quality, patterns, issues | Standard evidence required | "Review code quality", "Find tech debt" |
| `security` | Vulnerabilities: injection, auth, crypto, secrets | Cross-reference with OWASP; verify exploitability | "Find SQL injection", "Audit authentication" |
| `architecture` | Design: coupling, cohesion, patterns, dependencies | Verify with dependency graph evidence | "Find circular dependencies", "Map module coupling" |
| `performance` | Bottlenecks: complexity, I/O, memory, N+1 | Verify with complexity analysis | "Find N+1 queries", "Identify hot paths" |

**Step 2: Initialize with chosen agent type**

```bash
# Security audit
init ./src -q "Find all injection vulnerabilities and hardcoded credentials" --agent-type security

# Architecture review
init ./src -q "Identify circular dependencies and God classes" --agent-type architecture

# Performance analysis
init ./src -q "Find N+1 database queries and unnecessary allocations" --agent-type performance
```

When non-default agent type is used, init output shows:

```
  [Agent] Type: security
```

**Step 3: Complete the workflow**

The agent type affects the MAP phase -- each sub-agent receives specialized instructions. The rest of the workflow is identical:

```bash
exec -c "paths = write_chunks(size=150000); print(f'{len(paths)} chunks')"
map
reduce
export-results security-audit.json
```

**Step 4: Compare agent types (optional)**

For thorough analysis, run the same codebase with different agent types:

```bash
# Run 1: Security
init ./src -q "Full analysis" --agent-type security
# ... complete workflow ...
export-results security-results.json

# Run 2: Performance
init ./src -q "Full analysis" --agent-type performance --force
# ... complete workflow ...
export-results performance-results.json
```

### Success Criteria

- Init output shows the selected agent type
- Sub-agent findings are relevant to the chosen specialization
- Security agent finds vulnerabilities, not architecture issues (and vice versa)

### Common Pitfalls

| Problem | Cause | Fix |
|---------|-------|-----|
| Agent type not shown in output | Using the default (`general`) | Non-default types are shown; `general` is implied |
| Invalid agent type error | Typo in type name | Valid values: `general`, `security`, `architecture`, `performance` |
| Findings seem generic | Query doesn't match agent type | Align query with agent specialization |

### Documentation Needed

- **REFERENCE.md**: Specialized Agent Types table with detailed descriptions
- **SKILL.md**: Specialized Agents table (already exists)
- **GETTING-STARTED.md**: Brief mention of `--agent-type` as an advanced option

---

## Scenario 13: Using MAP Instructions Mode

**Persona:** P2 (Experienced Developer)
**Context:** The user wants more control over how sub-agents process chunks. Instead of automatic parallel processing, they want to see the generated prompts, execute them manually via the Task tool, and feed results back.
**Goal:** Use `map --instructions` to get sub-agent prompts, execute them manually, and record results.

### Prerequisites

- An initialized session with chunks created
- Claude Code environment (for Task tool execution)
- Understanding of the Task tool in Claude Code

### Step-by-step Workflow

**Step 1: Create chunks**

```bash
init ./src -q "Security audit"
exec -c "paths = write_chunks(size=150000); print(f'{len(paths)} chunks')"
```

**Step 2: Generate MAP instructions**

```bash
map --instructions
```

This outputs Task tool prompts for each chunk (default: first 5 chunks). The output includes:

```
=== MAP Instructions (Batch 1 of 2) ===

For each chunk below, create a Task with the following prompt:

--- Chunk 1/10 (ID: a1b2c3d4) ---
[Full sub-agent prompt with XML boundary structure, chunk content, and query]

--- Chunk 2/10 (ID: e5f6g7h8) ---
[...]
```

**Step 3: Control pagination**

```bash
# Show specific batch
map --instructions --batch 2

# Show more chunks per batch
map --instructions --limit 10

# Save instructions to a file
map --instructions --output instructions.txt
```

**Step 4: Execute prompts via Task tool**

In Claude Code, use the Task tool with each generated prompt. The sub-agent will return a JSON response:

```json
{
  "chunk_id": "a1b2c3d4",
  "status": "completed",
  "findings": [...],
  "missing_info": [],
  "partial_answer": "..."
}
```

**Step 5: Feed results back**

```bash
# Record individual result
exec -c 'add_result({"chunk_id": "a1b2c3d4", "status": "completed", "findings": [{"point": "Found issue", "evidence": "Line 10", "confidence": "high"}], "missing_info": [], "partial_answer": None})'

# Or import from a JSON file (max 10MB)
exec -c "result = add_results_from_file('chunk_results.json'); print(result)"
```

The `add_results_from_file` function returns `{"added": N, "errors": M}`.

**Step 6: Run reduce after all results are recorded**

```bash
reduce
export-results results.json
```

### Success Criteria

- `map --instructions` outputs valid sub-agent prompts
- Task tool execution with the prompts produces structured JSON responses
- `add_result` successfully records findings
- `reduce` aggregates all manually-recorded results

### Common Pitfalls

| Problem | Cause | Fix |
|---------|-------|-----|
| "All chunks already processed" | Results already recorded from a prior `map` run | Use `init --force` to start fresh |
| `add_result` validation error | Result doesn't match ChunkResult schema | Ensure required fields: `chunk_id`, `status`, `findings`, `missing_info` |
| Import file too large | File exceeds 10MB limit | Split into smaller files |
| Path traversal error on import | File path outside project | Use absolute path within the project directory |

### Documentation Needed

- **TROUBLESHOOTING.md**: "How to Use MAP Instructions Mode" workflow
- **REFERENCE.md**: `map` command with `--instructions`, `--batch`, `--limit`, `--output` flags
- **SKILL.md**: MAP section (already documents `map --instructions`)

---

## Scenario 14: Troubleshooting Performance Issues

**Persona:** P2 (Experienced Developer)
**Context:** A scan is running slowly, using too much memory, or timing out. The user needs to diagnose and improve performance.
**Goal:** Identify performance bottlenecks and apply optimizations.

### Prerequisites

- A scan that is running slower than expected
- Understanding of the scan phases (init, scout, chunk, map, reduce)

### Step-by-step Workflow

**Step 1: Identify the slow phase**

```bash
status
```

Check which phase the scan is stuck in:

| Phase | If Slow, Likely Cause |
|-------|-----------------------|
| `initialized` | Large file loading during init |
| `scouting` | Not a phase issue; user is exploring |
| `chunking` | Semantic (tree-sitter) parsing of large files |
| `mapping` | Sub-agent processing; API rate limits |
| `reducing` | Large number of findings to deduplicate |

**Step 2: Monitor progress**

```bash
# One-time progress check
progress

# Real-time monitoring
progress --watch
```

Or tail the progress file directly:

```bash
tail -f ~/.claude/cache/deepscan/{session_hash}/progress.jsonl
```

Progress events include `batch_start`, `batch_end`, `chunk_complete`, and `finding` entries.

**Step 3: Apply performance optimizations**

For slow **init** (file loading):
- Use `--lazy` to skip content loading
- Use `--target` to load only specific directories
- Add large binary or generated files to `.deepscanignore`
- Single file limit is 10MB; files exceeding this are auto-skipped

For slow **chunking**:
- Disable semantic chunking (use text-based): `write_chunks(size=150000, semantic=False)`
- Increase chunk size to reduce chunk count: `write_chunks(size=250000)`
- Dynamic timeout auto-adjusts based on context size

For slow **MAP**:
- Check chunk count: more chunks = more API calls
- Max recommended: 100 chunks (warning), hard limit: 500
- Reduce scope with `--target` or larger chunk sizes
- API rate limits (DS-504) require waiting and retrying

For slow **reduce**:
- Normal; deduplication is O(n^2) in worst case
- Token-based blocking optimization in `aggregator.py` makes it near-linear for diverse findings

**Step 4: Check memory usage**

If you have `psutil` installed, `chunk_files_safely` in `ast_chunker.py` monitors memory and triggers garbage collection at 500MB. Without `psutil`, GC runs every 50 files.

**Step 5: Use model escalation wisely**

```bash
map --escalate
```

Escalation retries failed chunks with Sonnet (more capable but slower and more expensive). Budget limits:
- Max 15% of total chunks can be escalated
- $5 Sonnet cost cap
- Only triggers for `QUALITY_LOW` and `COMPLEXITY` failures after attempt >= 2

### Success Criteria

- User identifies the slow phase
- Applied optimization reduces processing time
- Progress monitoring shows improvement

### Common Pitfalls

| Problem | Cause | Fix |
|---------|-------|-----|
| DS-503 timeout during exec | Default 5s too short for complex ops | Use `exec -c "..." --timeout 30` |
| Chunk count at 500 (blocked) | Context too large for chunk size | Increase chunk size or reduce context |
| Memory pressure on host | No resource limits (Windows) or large context | Use Docker with `--memory 1g` |
| Progress file grows large | Many events over time | Automatic rotation at 10MB (renames to `.jsonl.1`) |

### Documentation Needed

- **TROUBLESHOOTING.md**: Performance troubleshooting section
- **REFERENCE.md**: `progress` command, model escalation parameters
- **ARCHITECTURE.md**: Memory management description (exists)

---

## Scenario 15: Uninstalling/Disabling the Plugin

**Persona:** P1 (Beginner), P2 (Experienced)
**Context:** The user no longer needs DeepScan or wants to remove it cleanly, including all cached data.
**Goal:** Completely remove the DeepScan plugin and all associated data.

### Prerequisites

- DeepScan currently installed

### Step-by-step Workflow

**Step 1: Clean up all sessions**

```bash
# List existing sessions
poetry run python .claude/skills/deepscan/scripts/deepscan_engine.py list

# Clean old sessions (all older than 0 days = all sessions)
poetry run python .claude/skills/deepscan/scripts/deepscan_engine.py clean --older-than 0
```

**Step 2: Remove cached data**

```bash
rm -rf ~/.claude/cache/deepscan/
```

This removes:
- All session state files (`state.json`)
- All checkpoints (`checkpoint.json`)
- All chunk files (`chunks/`)
- All result files (`results/`)
- All progress logs (`progress.jsonl`)
- The current session marker (`.current_session`)

**Step 3: Remove the plugin registration**

```bash
claude plugin remove deepscan
```

Or if installed via git clone, remove the directories:

```bash
rm -rf .claude/skills/deepscan/
rm -rf .claude-plugin/
```

**Step 4: Verify removal**

```bash
# This should fail or not trigger DeepScan
claude plugin list  # DeepScan should not appear

# Trigger phrases should no longer activate the skill
# Type "analyze large codebase" in Claude Code -- should not invoke DeepScan
```

### Success Criteria

- No DeepScan sessions remain in cache
- Plugin no longer appears in `claude plugin list`
- Trigger phrases no longer activate the skill
- No leftover files in `~/.claude/cache/deepscan/`

### Common Pitfalls

| Problem | Cause | Fix |
|---------|-------|-----|
| Cache directory still exists | `clean` doesn't remove the directory itself | `rm -rf ~/.claude/cache/deepscan/` |
| Plugin still triggers | Plugin registration not removed | Use `claude plugin remove deepscan` |

### Documentation Needed

- **TROUBLESHOOTING.md**: "How to Uninstall DeepScan" section
- **README.md**: Brief mention of cleanup

---

## Summary: Scenario Coverage Matrix

| # | Scenario | Personas | Priority | Primary Doc |
|---|----------|----------|----------|-------------|
| 1 | Installation & First-Time Setup | P1, P2 | HIGH | GETTING-STARTED.md, README.md |
| 2 | Running a First Scan | P1 | HIGH | GETTING-STARTED.md |
| 3 | Interpreting Scan Results | P1, P2 | HIGH | GETTING-STARTED.md, README.md |
| 4 | Configuring Scan Parameters | P2 | MEDIUM | REFERENCE.md, USE_CASES.md |
| 5 | Incremental Scanning | P2 | MEDIUM | TROUBLESHOOTING.md, REFERENCE.md |
| 6 | Checkpoint and Resume | P1, P2 | HIGH | TROUBLESHOOTING.md |
| 7 | Using the REPL Sandbox | P1, P2 | HIGH | REFERENCE.md, TROUBLESHOOTING.md |
| 8 | Handling Errors | P1, P2 | HIGH | ERROR-CODES.md, TROUBLESHOOTING.md |
| 9 | Cancellation & Shutdown | P1, P2 | HIGH | TROUBLESHOOTING.md |
| 10 | Security & Sandbox | P3, P1 | HIGH | SECURITY.md, REFERENCE.md |
| 11 | Large Codebase Strategies | P2 | MEDIUM | USE_CASES.md, TROUBLESHOOTING.md |
| 12 | Custom Agent Types | P2 | MEDIUM | REFERENCE.md, SKILL.md |
| 13 | MAP Instructions Mode | P2 | MEDIUM | TROUBLESHOOTING.md, REFERENCE.md |
| 14 | Performance Troubleshooting | P2 | LOW | TROUBLESHOOTING.md, REFERENCE.md |
| 15 | Uninstalling the Plugin | P1, P2 | MEDIUM | TROUBLESHOOTING.md, README.md |

### Document Coverage

Every scenario is mapped to at least one document in the restructured documentation:

| Document | Scenarios Covered |
|----------|-------------------|
| **GETTING-STARTED.md** (Tutorial) | 1, 2, 3, 7 (basics), 12 (mention) |
| **TROUBLESHOOTING.md** (How-To) | 5, 6, 8, 9, 11, 13, 14, 15 |
| **REFERENCE.md** (Reference) | 4, 5, 6, 7, 9, 10, 11, 12, 13, 14 |
| **ERROR-CODES.md** (Reference) | 8 |
| **README.md** (Gateway) | 1, 3, 15 |
| **SKILL.md** (Quick Reference) | 2, 4, 12 |
| **SECURITY.md** (Explanation) | 10 |
| **USE_CASES.md** (How-To) | 4, 5, 11 |
| **ARCHITECTURE.md** (Explanation) | 3 (dedup/contradictions), 14 (memory) |

### Phase 1 Scenario ID Mapping

These 15 scenarios cover all 32 Phase 1 scenario ideas:

| Phase 1 IDs | Covered By Scenario |
|-------------|---------------------|
| 1.1, 1.2, 1.3, 2.2 | Scenario 1 (Installation) |
| 3.1, 3.2 | Scenario 2 (First Scan) |
| 4.1, 4.2, 4.3, 13.1 | Scenario 3 (Results) |
| 2.1, 5.1, 5.2, 5.3 | Scenario 4 (Configuration) |
| 7.1, 7.2 | Scenario 5 (Incremental) |
| 8.1, 8.2 | Scenario 6 (Checkpoint/Resume) |
| 9.1, 9.2, 9.3 | Scenario 7 (REPL) |
| 6.1, 6.2, 6.3, 6.4, 6.5 | Scenario 8 (Errors) |
| 20.1 | Scenario 9 (Cancellation) |
| 14.1, 14.2 | Scenario 10 (Security) |
| 10.1, 10.2, 11.1 | Scenario 11 (Large Codebase) |
| 12.1, 12.3 | Scenario 12 (Agent Types) |
| 12.2 | Scenario 13 (MAP Instructions) |
| 15.1, 21.1, 21.2 | Scenario 14 (Performance) |
| 16.1, 17.1 | Scenario 15 (Uninstall) |
| 3.3, 19.1 | Cross-cutting (covered in multiple scenarios: CLI vs Claude Code in 2/7/11; CLI shortcuts in REFERENCE.md) |
| 18.1 (CI/CD) | Deferred -- MAP requires Claude Code environment, making CI/CD impractical currently |
