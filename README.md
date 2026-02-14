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

## Installation

Add to your Claude Code project as a plugin:

```bash
claude plugin add idnotbe/deepscan
```

Or clone and add locally:

```bash
git clone https://github.com/idnotbe/deepscan.git
```

## Usage

```
/deepscan init ./src -q "Find all security vulnerabilities"
```

See the [skill documentation](.claude/skills/deepscan/SKILL.md) for the full command reference.

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

## Documentation

- [SKILL.md](.claude/skills/deepscan/SKILL.md) - Full command reference
- [Architecture](.claude/skills/deepscan/docs/ARCHITECTURE.md) - System design
- [Security](.claude/skills/deepscan/docs/SECURITY.md) - Threat model and defenses
- [Use Cases](.claude/skills/deepscan/docs/USE_CASES.md) - Detailed scenarios

## License

MIT License - See [LICENSE](LICENSE) for details.
