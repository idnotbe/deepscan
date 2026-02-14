# DeepScan - Large Context Analysis System

**Version**: 2.0.0 (Phase 7)
**Status**: ✅ Full Feature Set

## Overview

DeepScan is a large context analysis system for Claude Code that processes 100+ files or >1MB data through chunking and REPL-based analysis to **prevent context rot** (LLM performance degradation in long contexts).

## Design Goals & Rationale

### Why DeepScan Exists

Large Language Models have a fundamental limitation: **context rot**. When processing very long contexts:
- Models lose precision on information from early in the context
- Token costs become prohibitive for large codebases
- Response quality degrades unpredictably

Simple solutions like "read the whole codebase" or "grep and summarize" don't work for tasks that require:
- **Precision lookup**: "Find exactly where this function is called, with line numbers"
- **Multi-hop reasoning**: "Trace data flow from API endpoint to database query"
- **Evidence tracking**: "Show me the code that proves this vulnerability exists"

### How DeepScan Solves This

DeepScan implements a **chunked map-reduce pattern**:

1. **Load** large context into external storage (not LLM context)
2. **Chunk** into manageable pieces (~150K characters each)
3. **Map** chunks to parallel sub-agents (lightweight Haiku models)
4. **Reduce** findings with deduplication and conflict resolution

Each sub-agent sees only its chunk, staying within optimal context limits. The aggregator synthesizes findings while preserving evidence and source locations.

### Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Precision over Summary** | Every finding includes file path, line numbers, and evidence |
| **Evidence-based** | Sub-agents must cite specific code snippets |
| **Resumable** | Checkpoints after each batch; resume on failure |
| **Secure by Default** | REPL sandboxed with multi-layer defense (see [SECURITY.md](docs/SECURITY.md)) |
| **Progressive Disclosure** | Simple commands for common tasks, full power when needed |

### When to Use DeepScan

| Scenario | DeepScan? | Why |
|----------|-----------|-----|
| Analyze 100+ file codebase | Yes | Prevents context rot |
| Find all API endpoints | Yes | Multi-file aggregation needed |
| Read a single config file | No | Standard Read tool is sufficient |
| Grep for a known pattern | No | Grep tool is faster |
| Security audit with evidence | Yes | Needs precise source citations |

For detailed architecture, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

### Phase 7 Features

✅ **Core Features**:
- JSON-based state persistence (`~/.claude/cache/deepscan/`)
- Fixed-size and adaptive chunking (content-type aware)
- REPL helper functions (peek, grep, chunk_indices, write_chunks)
- Sandboxed code execution (SAFE_BUILTINS + AST validation)
- CLI interface (init, status, exec, reset, export-results, map, progress, list, resume, abort, clean)
- Pydantic data models for type safety
- Security features (path traversal protection, input sanitization, prompt injection protection)

✅ **Parallel Processing**:
- `map` command for parallel sub-agent spawning
- `map --instructions` for manual Task tool integration
- Batch processing (default 5 parallel agents)
- Graceful degradation (parallel → sequential on >50% batch failure)
- Checkpoint after each batch

✅ **Advanced Features**:
- Incremental re-analysis (delta chunks only via file hash manifest)
- Adaptive chunk sizing based on content type (code=100K, config=80K, docs=200K)
- Model escalation (haiku → sonnet on quality/complexity failures)
- Progress streaming (JSONL for real-time monitoring)
- Session management (list, resume, abort, clean)
- Result aggregation with deduplication and contradiction detection

> **Note**: CLI mode provides placeholder results. Full sub-agent processing requires Claude Code environment.

### ⚠️ Model Quality Trade-offs (D2-FIX)

DeepScan uses **Haiku** by default for cost efficiency, but this affects analysis quality:

| Model | Cost | Quality | Best For |
|-------|------|---------|----------|
| **Haiku** (default) | Low (~$0.25/1M tokens) | Moderate | Simple pattern matching, basic code scanning |
| **Sonnet** (recommended) | Higher (~$3/1M tokens) | High | Complex reasoning, security audits, architecture analysis |

**Quality Issues with Haiku:**
- May produce false positives (claiming things are deprecated when they're not)
- Struggles with multi-hop reasoning (tracing dependencies across files)
- Can misinterpret complex documentation relationships

**Recommendation:** For important analyses, use Sonnet:
```
# In your Task tool prompt for sub-agents:
model: "sonnet"
```

DeepScan automatically escalates to Sonnet when:
- A chunk fails with `QUALITY_LOW` status
- Analysis complexity exceeds Haiku's capability
>
> For comprehensive feature documentation, see [SKILL.md](SKILL.md#phase-7-features).

## Quick Start

### 1. Initialize

```bash
poetry run python .claude/skills/deepscan/scripts/deepscan_engine.py init <path> [-q "query"]
```

Example:
```bash
poetry run python .claude/skills/deepscan/scripts/deepscan_engine.py init ./src -q "Find all API endpoints"
```

### 2. Explore Context

```bash
# View first 5000 characters
poetry run python .claude/skills/deepscan/scripts/deepscan_engine.py exec -c "print(peek_head(5000))"

# Search for patterns (max_matches limits results, window shows context)
poetry run python .claude/skills/deepscan/scripts/deepscan_engine.py exec -c "results = grep('TODO|FIXME', max_matches=50); print(f'{len(results)} matches')"

# Get context size
poetry run python .claude/skills/deepscan/scripts/deepscan_engine.py exec -c "print(f'{context_length():,} characters')"
```

### 3. Create Chunks

```bash
poetry run python .claude/skills/deepscan/scripts/deepscan_engine.py exec -c "paths = write_chunks(size=150000, overlap=10000); print(f'Created {len(paths)} chunks')"
```

### 4. Check Status

```bash
poetry run python .claude/skills/deepscan/scripts/deepscan_engine.py status
```

### 5. Export Results

```bash
poetry run python .claude/skills/deepscan/scripts/deepscan_engine.py export-results output.json
```

## Complete Workflow Example (P5.2)

This section shows the complete `init → map → reduce` workflow with expected outputs.

### Step 1: Initialize Session

```bash
$ deepscan init ./src -q "Find security vulnerabilities"

[OK] DeepScan initialized
  Session: deepscan_1706500000_abc123def456
  Context: ./src
  Size: 2,450,000 characters
  Files: 156
```

### Step 2: Create Chunks and Run MAP Phase

```bash
# Create chunks
$ deepscan exec -c "paths = write_chunks(size=150000); print(f'Created {len(paths)} chunks')"
Created 17 chunks

# Generate Task tool prompts (for Claude Code)
$ deepscan map --instructions -o prompts.md
[OK] Instructions written to prompts.md
     Total chunks: 17

# Or run directly in CLI (generates placeholders)
$ deepscan map
[MAP] Processing batch 1/4 (5 chunks)
...
```

### Step 3: Monitor Progress (Optional)

```bash
# One-time status check
$ deepscan progress

[PROGRESS] Session: deepscan_1706500000_abc123def456
  Phase: map
  Progress: 35.3%
  Chunks: 6/17 completed

# Real-time monitoring
$ deepscan progress --watch
[WATCH] Monitoring progress (Ctrl+C to stop)...
[14:32:15] Phase: map | Progress: 41.2% | Chunks: 7/17 (+2 events)
```

### Step 4: Run REDUCE Phase

```bash
$ deepscan reduce

[REDUCE COMPLETE]
  Total findings: 42
  Unique findings: 28
  Deduplication: 33.3%

[TOP FINDINGS]
  1. [high] SQL injection vulnerability in user_query.py:145
  2. [high] Unvalidated file path in upload_handler.py:89
  ...
```

### Step 5: Export Results

```bash
$ deepscan export-results security_audit.json
[OK] Results exported to security_audit.json
```

## Resuming Work

DeepScan supports session persistence and resumption for interrupted analyses.

### View Available Sessions

```bash
$ deepscan list

=== DeepScan Sessions (3) ===

Hash                                          Phase        Progress   Modified
------------------------------------------------------------------------------------------
deepscan_1706500000_abc123def456              map          65.0%      2026-01-29 14:30
deepscan_1706400000_def789abc012              completed    100.0%     2026-01-28 10:15
deepscan_1706300000_ghi345jkl678              initialized  0.0%       2026-01-27 09:00

(Current: deepscan_1706500000_abc123def456)
```

### Resume a Session

```bash
# Resume most recent session
$ deepscan resume
Resuming most recent session: deepscan_1706500000_abc123def456
[OK] Resumed session: deepscan_1706500000_abc123def456
  Phase: map
  Progress: 65.0%
  Chunks: 17 total, 11 processed

# Resume specific session
$ deepscan resume deepscan_1706400000_def789abc012
```

### Handle Session Conflicts

If you try to initialize a new session while one is active:

```bash
$ deepscan init ./new_project -q "New analysis"

[WARNING] Active session already exists:
  Session: deepscan_1706500000_abc123def456

Options:
  • Use --force to overwrite the existing session
  • Use 'deepscan resume' to continue the existing session
  • Use 'deepscan abort <session>' to delete it first
```

### Clean Up Old Sessions

```bash
# Delete sessions older than 7 days (default)
$ deepscan clean
[OK] Cleaned 2 sessions, freed 15.32 MB

# Delete sessions older than 3 days
$ deepscan clean --older-than 3
```

## Helper Functions

Available in `exec -c` commands:

| Function | Args | Returns | Description |
|----------|------|---------|-------------|
| `peek(start, end)` | `int, int` | `str` | View context slice |
| `peek_head(n)` | `int` | `str` | First n chars |
| `peek_tail(n)` | `int` | `str` | Last n chars |
| `grep(pattern, max_matches, window)` | `str, int=20, int=100` | `list[dict]` | Regex search with ReDoS protection |
| `grep_file(pattern, filepath, ...)` | `str, str, int=20, int=100` | `list[dict]` | Search specific file (works in lazy mode) |
| `chunk_indices(size, overlap)` | `int, int` | `list[tuple]` | Calculate chunk boundaries |
| `write_chunks(out_dir, size, overlap, semantic)` | `str\|None, int=150000, int=0, bool=False` | `list[str]` | Create chunk files (semantic=True for AST-based) |
| `add_buffer(text)` | `str` | `-` | Add to result buffer |
| `get_buffers()` | `-` | `list[str]` | Get all buffers |
| `clear_buffers()` | `-` | `-` | Clear all result buffers |
| `add_result(result)` | `dict` | `-` | Add chunk result |
| `set_final_answer(answer)` | `str` | `-` | Set final answer |
| `get_status()` | `-` | `dict` | State summary |
| `context_length()` | `-` | `int` | Total characters |
| `is_lazy_mode()` | `-` | `bool` | Check if lazy mode is active |
| `get_tree_view()` | `-` | `str` | Directory tree (works in both lazy and full mode) |
| `preview_dir(subpath, max_depth, max_files)` | `str, int=2, int=30` | `str` | Preview subdirectory structure |
| `load_file(filepath)` | `str` | `str` | Load specific file content |

> **Note**: `get_tree_view()`, `preview_dir()`, and `load_file()` work in **both lazy and full mode**.
> In lazy mode, they are the primary navigation tools. In full mode, they generate tree views on-demand.

## Project Layout

```
~/.claude/cache/deepscan/{session_hash}/
├── state.json                    # Pydantic DeepScanState
├── chunks/
│   ├── chunk_0000.txt
│   ├── chunk_0001.txt
│   └── ...
├── results/                      # Aggregated results
└── progress.jsonl                # Real-time progress stream

.claude/skills/deepscan/
├── SKILL.md                      # Skill definition (triggers, tools)
├── scripts/
│   ├── __init__.py
│   ├── models.py                 # Pydantic schemas (~150 LOC)
│   ├── deepscan_engine.py        # Main engine (~2500 LOC)
│   ├── subagent_prompt.py        # Sub-agent prompts (embedded, ~400 LOC)
│   ├── aggregator.py             # Result aggregation (~600 LOC)
│   ├── checkpoint.py             # Checkpoint management (~280 LOC)
│   ├── cancellation.py           # Work cancellation (~460 LOC)
│   ├── incremental.py            # Delta analysis (~530 LOC)
│   ├── error_codes.py            # Error code system (~450 LOC)
│   └── ast_chunker.py            # Semantic chunking (~1000 LOC)
└── README.md                     # This file
```

> **Note**: Sub-agent prompts are embedded in `subagent_prompt.py` rather than external
> agent definition files. This enables better type safety and inline template management.

## Security

### Sandboxed REPL Execution

- **Restricted builtins**: No `__import__`, `eval`, `exec`, `open`, `os`, etc.
- **AST validation**: Blocks dangerous node types and attribute access
- **Pattern blocking**: Regex-based forbidden pattern detection

### File Access

- **Write isolation**: Only `~/.claude/cache/deepscan/` writable
- **Size limits**: 10MB/file, 50MB total context
- **Path traversal protection**: Resolved path validation

### Serialization

- **JSON only**: No pickle (prevents arbitrary code execution)
- **Pydantic validation**: Type-safe schema enforcement

## Known Limitations (Phase 7)

> **Resolved (2026-01-26)**: Background task output timing issue has been fixed
> by switching to foreground mode. Parallel execution is maintained via multiple
> Task calls in a single message. See ERROR_REPORT_DEEPSCAN_SKILLS.md Issue #5.

### 1. CLI Mode vs Claude Code Environment

**Issue**: Standalone CLI (`map` command) produces placeholder results, not actual analysis.

**Reason**: Real sub-agent processing requires Claude Code's Task tool which is unavailable in CLI mode.

**Workaround**:
```bash
# Use --instructions flag to get prompts for manual Task tool execution
poetry run python .claude/skills/deepscan/scripts/deepscan_engine.py map --instructions
```

### 2. Model Escalation Budget

**Issue**: Sonnet usage is capped at 15% of chunks and $5 per session.

**Reason**: Cost control. Escalation is for edge cases, not default behavior.

**Workaround**: Manually re-run failed chunks with explicit sonnet model if needed.

### 3. Platform-Specific Path Handling

**Issue**: Path handling tested primarily on Linux/macOS.

**Workaround**: Windows users should use forward slashes or raw strings for paths.

### 4. Execution Mode Behavior

**Behavior**: The `exec` command uses two different execution paths:

| Code Type | Execution Mode | Reason |
|-----------|----------------|--------|
| Simple code (no helpers) | Subprocess | Isolation, can be terminated on timeout |
| Helper functions (grep, peek, etc.) | Main process | Requires StateManager closure |

**Key Points**:
- **No state persistence between exec calls**: Each `exec -c "..."` is a fresh context
- **Variables are NOT preserved**: Define and use variables in the same exec call
- **State management**: Use `add_buffer()`, `add_result()`, `set_final_answer()` for persistence

**Timeout Behavior (Phase 8)**:
- Simple commands: 5 seconds default
- `write_chunks`: Auto-calculated (2s/MB, min 30s, max 120s)
- Manual override: `exec -c "..." --timeout 60`

### 5. REPL Syntax Restrictions

**Allowed**: Variables, loops, conditionals, comprehensions, lambdas, f-strings
**Blocked**: Function/class definitions, imports, try/except, async, global/nonlocal

## Development

### Project Standards

- **Type checking**: `mypy --strict` (enforced)
- **Line length**: 100 characters
- **Testing**: `pytest` with `@pytest.mark.unit` markers
- **Security**: `bandit` SAST scanning

### Running Tests

```bash
# Unit tests (when implemented)
poetry run pytest tests/unit/deepscan/ -v

# Type checking
poetry run mypy .claude/skills/deepscan/scripts/ --strict

# Security scan
poetry run bandit -r .claude/skills/deepscan/scripts/
```

### File Metrics

- `deepscan_engine.py`: ~2500 LOC (StateManager + REPL + CLI + MAP/REDUCE)
- `subagent_prompt.py`: ~400 LOC (Embedded agent prompts + sanitization)
- `aggregator.py`: ~600 LOC (Result aggregation + FINAL markers)
- `ast_chunker.py`: ~1000 LOC (Semantic chunking with AST)
- `incremental.py`: ~530 LOC (Delta analysis)
- `cancellation.py`: ~460 LOC (Work cancellation)
- `error_codes.py`: ~450 LOC (Error handling)
- `checkpoint.py`: ~280 LOC (Checkpoint management)
- `models.py`: ~150 LOC (Pydantic schemas)
- **Total**: ~6370 LOC (excluding tests)

## Roadmap

### ✅ Phase 1-6: Completed
- Phase 1: Core chunking + REPL engine
- Phase 2: Parallel processing + checkpoint recovery
- Phase 3: Security hardening
- Phase 4: Adaptive chunking + model escalation
- Phase 5: Specialized agent types + incremental re-analysis
- Phase 6: Error code system + work cancellation
- Phase 7: Full feature integration + documentation

### Phase 8 (Future): Semantic Chunking
- AST-based chunking for language-aware boundaries
- Cross-file dependency tracking
- Improved aggregation with semantic deduplication

## Contributing

Follow TDD protocol:
1. Write test first (RED)
2. Implement feature (GREEN)
3. Refactor (REFACTOR)

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for system design and extension points.

## References

- **Architecture**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - System design and data flow
- **Security**: [docs/SECURITY.md](docs/SECURITY.md) - Threat model and defense layers
- **ADR-001**: [docs/ADR-001-repl-security-relaxation.md](docs/ADR-001-repl-security-relaxation.md) - REPL security decisions

## License

Part of Ops project.
