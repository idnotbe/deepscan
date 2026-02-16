# DeepScan

Deep multi-file analysis plugin for Claude Code. Handles complex tasks where standard context windows fail or "context rot" occurs.

## What It Does

DeepScan implements a chunked map-reduce pattern to analyze large codebases:

1. **Load** large context into external storage (not LLM context)
2. **Chunk** into manageable pieces (~150K characters each)
3. **Map** chunks to parallel sub-agents (specialized by type)
4. **Reduce** findings with deduplication and conflict resolution

Each sub-agent sees only its chunk, staying within optimal context limits. The aggregator synthesizes findings while preserving evidence and source locations.

## When to Use

- Analyzing 100+ file codebases
- Security audits requiring precise source citations
- Architecture reviews across many modules
- Tracing data flow through multiple files
- Any multi-hop reasoning across distributed sources

## When NOT to Use

- Single-file lookups (use Grep)
- File discovery (use Glob)
- Reading 1-3 specific files (use Read)
- Simple pattern matching

## Prerequisites

- **Python 3.10+** (uses `X | None` syntax)
- **pydantic** (`pip install pydantic`)
- **Claude Code** installed and working
- **Poetry** (for CLI verification; `pip install poetry`) -- or use `python3` directly

Optional: `tree-sitter-language-pack` (semantic chunking), `xxhash` (faster hashing), `rich` (styled errors), `psutil` (memory-aware chunking).

## Installation

Add to your Claude Code project as a plugin:

```bash
claude plugin add idnotbe/deepscan
```

Or clone and add locally:

```bash
git clone https://github.com/idnotbe/deepscan.git
```

Verify the installation:

```bash
poetry run python .claude/skills/deepscan/scripts/deepscan_engine.py --help
```

## Quick Example

```
/deepscan init ./src -q "Find all security vulnerabilities"
```

After completing the scan workflow (init, chunk, map, reduce, export), you get structured findings:

```json
{
  "point": "SQL injection vulnerability",
  "evidence": "Line 45: query = f\"SELECT * FROM users WHERE id={user_id}\"",
  "confidence": "high",
  "location": {"file": "src/db.py", "line": 45}
}
```

See the [Getting Started guide](.claude/skills/deepscan/docs/GETTING-STARTED.md) for a complete walkthrough.

## Specialized Agents

| Type | Focus |
|------|-------|
| general | Broad code analysis (default) |
| security | Vulnerabilities, credentials, injections |
| architecture | Design patterns, coupling, dependencies |
| performance | Bottlenecks, complexity, efficiency |

## Key Features

- **Checkpoints**: Auto-save after each batch, resume on failure
- **Incremental**: Delta analysis via file hash manifest (3-10x faster)
- **Progress Streaming**: Real-time monitoring via JSONL
- **Deduplication**: Similarity threshold 0.7
- **Model Escalation**: Automatic haiku to sonnet on quality failures
- **Sandboxed REPL**: Multi-layer security for safe execution
- **Cancellation**: Graceful Ctrl+C with checkpoint save, double Ctrl+C to force quit
- **Semantic Chunking**: AST-based chunking for Python, JavaScript, TypeScript, Java, Go

## Testing

**No tests exist yet.** This is a critical gap for a plugin with security-sensitive code (sandboxed REPL execution, path traversal protection, AST validation).

When tests are created:

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=.claude/skills/deepscan/scripts --cov-report=html
```

Security-critical components that need test coverage:
- `repl_executor.py` -- sandboxed eval/exec, timeout enforcement
- `deepscan_engine.py` -- forbidden patterns, AST whitelist, attribute blocking
- `constants.py` -- SAFE_BUILTINS allowlist
- `state_manager.py` -- path containment via `_safe_write()`
- `walker.py` -- symlink safety, path traversal protection
- `ast_chunker.py` -- project-root enforcement

See [TEST-PLAN.md](TEST-PLAN.md) for the full prioritized test plan and [CLAUDE.md](CLAUDE.md) for developer guidance.

## Documentation

| Document | Description |
|----------|-------------|
| [Getting Started](.claude/skills/deepscan/docs/GETTING-STARTED.md) | Step-by-step tutorial for first-time users |
| [SKILL.md](.claude/skills/deepscan/SKILL.md) | Skill interface and quick command reference |
| [Reference](.claude/skills/deepscan/docs/REFERENCE.md) | Complete command, config, and REPL sandbox reference |
| [Error Codes](.claude/skills/deepscan/docs/ERROR-CODES.md) | All DS-NNN error codes with causes and fixes |
| [Troubleshooting](.claude/skills/deepscan/docs/TROUBLESHOOTING.md) | Common errors and workflow recipes |
| [Architecture](.claude/skills/deepscan/docs/ARCHITECTURE.md) | System design |
| [Security](.claude/skills/deepscan/docs/SECURITY.md) | Threat model and defenses |
| [Use Cases](.claude/skills/deepscan/docs/USE_CASES.md) | Detailed scenarios |

## License

MIT License - See [LICENSE](LICENSE) for details.
