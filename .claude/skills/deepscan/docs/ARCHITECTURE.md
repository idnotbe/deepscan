# DeepScan Architecture

> **Purpose**: This document describes the architecture of DeepScan for contributors and users who need to understand the system internals.

## 1. Design Goals

### 1.1 Problem Statement

Large Language Models suffer from **Context Rot** - performance degradation when processing very long contexts. When analyzing codebases with 100+ files or >1MB of text:
- Models lose precision in early-context information
- Token costs become prohibitive
- Response quality degrades unpredictably

### 1.2 Solution Approach

DeepScan implements a **chunked analysis pattern**:
1. Load large context into external storage (not LLM context)
2. Split into manageable chunks (~150K characters)
3. Process chunks in parallel via sub-agents
4. Aggregate findings with deduplication

This approach keeps each LLM call within optimal context limits while enabling analysis of arbitrarily large codebases.

### 1.3 Core Principles

| Principle | Implementation |
|-----------|----------------|
| **Precision over Summary** | Track exact line numbers and file paths |
| **Evidence-based** | Every finding includes source evidence |
| **Resumable** | Checkpoints after each batch |
| **Secure** | Sandboxed REPL with multi-layer defense |

---

## 2. High-Level Architecture

```
                         CLAUDE CODE ENVIRONMENT

    +-----------------------------------------------------------------+
    |                     ROOT AGENT (Sonnet/Opus)                     |
    |                                                                  |
    |   +------------------+      +------------------------------+     |
    |   |   SKILL.md       |----->|        ORCHESTRATOR          |     |
    |   |   (Triggers)     |      |   - Workflow management      |     |
    |   +------------------+      |   - Sub-agent coordination   |     |
    |                             +------------------------------+     |
    +-----------------------------------------------------------------+
                                     |
                                     v
    +-----------------------------------------------------------------+
    |                    REPL ENGINE (Python)                          |
    |                                                                  |
    |   +-----------------+  +----------------+  +------------------+  |
    |   | State Manager   |  | Context Store  |  | Helper Functions |  |
    |   | (Pydantic+JSON) |  | (Memory/Disk)  |  | peek/grep/chunk  |  |
    |   +-----------------+  +----------------+  +------------------+  |
    +-----------------------------------------------------------------+
                         |           |           |
                         v           v           v
    +-----------------+  +-----------------+  +-----------------+
    |  SUB-AGENT #1   |  |  SUB-AGENT #2   |  |  SUB-AGENT #N   |
    |  (Haiku)        |  |  (Haiku)        |  |  (Haiku)        |
    |  Task tool      |  |  Task tool      |  |  Task tool      |
    +-----------------+  +-----------------+  +-----------------+
                         |
                         v
    +-----------------------------------------------------------------+
    |                    RESULT AGGREGATOR                             |
    |                                                                  |
    |   - Collect Sub-Agent outputs                                   |
    |   - Parse FINAL()/FINAL_VAR() markers                           |
    |   - Deduplicate findings                                        |
    |   - Synthesize final answer                                     |
    +-----------------------------------------------------------------+
                                     |
                                     v
    +-----------------------------------------------------------------+
    |                 STATE PERSISTENCE (User Cache)                   |
    |                                                                  |
    |   Location: ~/.claude/cache/deepscan/{session_hash}/            |
    |   +-- state.json           (Main state)                         |
    |   +-- checkpoint.json      (Recovery point)                     |
    |   +-- chunks/              (Chunk files)                        |
    |   +-- results/             (Sub-agent results)                  |
    |   +-- progress.jsonl       (Real-time progress)                 |
    +-----------------------------------------------------------------+
```

---

## 3. Component Design

### 3.1 SKILL.md (Skill Interface)

**Location**: `.claude/skills/deepscan/SKILL.md`

Defines:
- Trigger phrases for skill activation
- Allowed tools (Read, Write, Edit, Bash, Task, Grep, Glob)
- Workflow instructions for the root agent

### 3.2 REPL Engine

**Location**: `.claude/skills/deepscan/scripts/deepscan_engine.py`

The core Python engine providing:
- Context loading and storage
- Sandboxed code execution for exploration
- Chunk management
- CLI interface

### 3.3 State Manager

Manages session state using Pydantic models serialized to JSON:

```python
class DeepScanState(BaseModel):
    version: str
    session_id: str
    phase: str  # initialized, scouting, chunking, mapping, reducing, completed
    config: DeepScanConfig
    context_meta: ContextMetadata
    chunks: list[ChunkInfo]
    results: list[ChunkResult]
    progress_percent: float
```

**Why Pydantic + JSON?**
- Type safety via Pydantic validation
- Human-readable state files
- No security risks (unlike pickle)

### 3.4 Sub-Agent System

Sub-agents process individual chunks using Claude Code's Task tool:

| Property | Value |
|----------|-------|
| Model | Haiku (cost-effective) |
| Execution | Foreground (stable output) |
| Concurrency | 5 parallel agents per batch (via multiple Task calls) |
| Escalation | haiku → sonnet on quality failures |

**Analysis Focus** (via `--agent-type` flag or `-q` query parameter):
- General: Broad code analysis (default)
- Security: Vulnerability detection (`--agent-type security`)
- Architecture: Design pattern analysis (`--agent-type architecture`)
- Performance: Bottleneck identification (`--agent-type performance`)

> **Note**: The `--agent-type` CLI flag is fully implemented (Phase 7). Use `-q` query for additional context.

### 3.5 Aggregator

**Location**: `.claude/skills/deepscan/scripts/aggregator.py`

Combines sub-agent findings with:
- **Deduplication**: Jaccard similarity (threshold: 0.7)
- **Contradiction detection**: Conflicting findings flagged
- **Confidence scoring**: High/Medium/Low ratings
- **Source tracking**: Original chunk and line numbers preserved

---

## 4. Workflow Phases

### 4.1 Main Workflow

```
    +------------+
    |   START    |
    +-----+------+
          |
          v
    +------------+      +-------------------+
    | INITIALIZE |----->| Load context      |
    |            |      | Create state      |
    +-----+------+      | Save checkpoint   |
          |             +-------------------+
          v
    +------------+      +-------------------+
    |   SCOUT    |----->| peek() context    |
    |            |      | grep() patterns   |
    +-----+------+      | Assess strategy   |
          |             +-------------------+
          v
    +------------+      +-------------------+
    |   CHUNK    |----->| Calculate spans   |
    |            |      | Write chunk files |
    +-----+------+      +-------------------+
          |
          v
    +------------+      +-------------------+
    |    MAP     |----->| Spawn sub-agents  |
    | (Parallel) |      | Collect results   |
    +-----+------+      | Handle failures   |
          |             +-------------------+
          v
    +------------+      +-------------------+
    |   REDUCE   |----->| Aggregate results |
    |            |      | Synthesize answer |
    +-----+------+      +-------------------+
          |
          v
    +------------+
    |    END     |
    +------------+
```

### 4.2 Error Recovery

| Failure Type | Strategy |
|--------------|----------|
| Sub-agent timeout | Retry up to 3 times |
| >50% batch failure | Fall back to sequential |
| Parse error | Re-prompt with structured format |
| Model quality issue | Escalate to sonnet |

Checkpoints are saved after each batch, enabling resume from failures.

---

## 5. Data Models

### 5.1 Core Schemas

```python
class ChunkInfo(BaseModel):
    chunk_id: str        # "chunk_0001"
    file_path: str       # Absolute path to chunk file
    start_offset: int    # Character offset in context
    end_offset: int
    size: int
    status: str          # pending, processing, completed, failed

class Finding(BaseModel):
    point: str           # "Found SQL injection vulnerability"
    evidence: str        # "Line 45: query = f'SELECT * FROM {user_input}'"
    confidence: str      # high, medium, low
    location: dict       # {"file": "app.py", "line": 45}

class ChunkResult(BaseModel):
    chunk_id: str
    status: str          # completed, partial, failed
    findings: list[Finding]
    missing_info: list[str]
    partial_answer: Optional[str]
```

### 5.2 Session Hash Format

```
deepscan_{timestamp}_{random_hex}
Example: deepscan_1737284400_a1b2c3d4e5f6
```

Uses `secrets.token_hex(8)` for cryptographic randomness.

---

## 6. File Structure

```
.claude/skills/deepscan/
|-- README.md              # Entry point, usage guide
|-- SKILL.md               # Claude interface definition
|-- docs/
|   |-- GETTING-STARTED.md # Tutorial walkthrough
|   |-- REFERENCE.md       # Complete command/config/REPL reference
|   |-- ERROR-CODES.md     # All 31 DS-NNN error codes
|   |-- TROUBLESHOOTING.md # Common errors and workflow recipes
|   |-- ARCHITECTURE.md    # This file
|   |-- SECURITY.md        # Security architecture
|   |-- USE_CASES.md       # Detailed scenarios
|   +-- ADR-001-repl-security-relaxation.md
+-- scripts/
    |-- __init__.py           # Package init (~30 LOC)
    |-- deepscan_engine.py    # Main engine + CLI (~2500 LOC)
    |-- models.py             # Pydantic schemas (~150 LOC)
    |-- constants.py          # Shared constants, SAFE_BUILTINS (~360 LOC)
    |-- aggregator.py         # Result aggregation (~600 LOC)
    |-- subagent_prompt.py    # Sub-agent prompts (~400 LOC)
    |-- ast_chunker.py        # Semantic chunking (~1000 LOC)
    |-- state_manager.py      # State persistence (~730 LOC)
    |-- helpers.py            # REPL helper functions (~650 LOC)
    |-- incremental.py        # Delta analysis (~530 LOC)
    |-- cancellation.py       # Work cancellation (~460 LOC)
    |-- error_codes.py        # Error code system (~450 LOC)
    |-- checkpoint.py         # Checkpoint management (~280 LOC)
    |-- repl_executor.py      # Subprocess REPL (~310 LOC)
    |-- walker.py             # Directory traversal (~220 LOC)
    |-- progress.py           # Progress streaming (~180 LOC)
    +-- grep_utils.py         # ReDoS-protected grep (~170 LOC)

~/.claude/cache/deepscan/{session_hash}/
|-- state.json             # Main state file
|-- checkpoint.json        # Recovery checkpoint
|-- chunks/
|   |-- chunk_0000.txt
|   +-- ...
|-- results/
|   +-- result_*.json
+-- progress.jsonl         # Real-time progress stream
```

---

## 7. Extension Points

### 7.1 Adding Custom Agent Types

> **Status**: Fully implemented (Phase 7). CLI `--agent-type` flag is connected.

The system supports agent type specialization via `AGENT_TYPE_INSTRUCTIONS`:

```python
# In scripts/subagent_prompt.py
SUPPORTED_AGENT_TYPES = ["general", "security", "architecture", "performance"]
AGENT_TYPE_INSTRUCTIONS = {
    "general": "...",
    "security": "...",
    "your_type": "Your custom prompt here"
}

def generate_subagent_prompt(..., agent_type: AgentType = "general"):
    # Uses AGENT_TYPE_INSTRUCTIONS[agent_type] for specialized prompts
```

**Usage:**
```bash
deepscan init ./src --agent-type security -q "Find vulnerabilities"
```

**To add new agent types:**
1. Add type to `SUPPORTED_AGENT_TYPES` in `subagent_prompt.py`
2. Add instructions to `AGENT_TYPE_INSTRUCTIONS` dict
3. Update CLI choices in `deepscan_engine.py` `init_parser` (search for `--agent-type` in `init_parser`)

### 7.2 Custom Chunking Strategies

The `ast_chunker.py` module supports language-aware chunking. To add a new language:

1. Add file extension mapping
2. Implement AST parsing for the language
3. Register in `get_chunker_for_extension()`

### 7.3 Result Aggregation Customization

Override aggregation in `aggregator.py`:
- `similarity_threshold`: Deduplication sensitivity (default: 0.7)
- `confidence_weights`: How to weight different confidence levels

---

## 8. Performance Characteristics

| Metric | Typical Value |
|--------|---------------|
| Chunk processing time | 5-30 seconds per chunk |
| Parallel batch size | 5 agents |
| Memory per chunk | ~1MB |
| State file size | 10-100KB |

**Optimizations**:
- Adaptive chunk sizing (code: 100K, config: 80K, docs: 200K)
- Token-based blocking in aggregator (O(n) vs O(n^2))
- Incremental re-analysis via file hash manifest

---

## References

- [Getting Started](GETTING-STARTED.md) - Step-by-step tutorial
- [Reference](REFERENCE.md) - Complete command, config, and REPL reference
- [Error Codes](ERROR-CODES.md) - All 31 DS-NNN error codes
- [Troubleshooting](TROUBLESHOOTING.md) - Common errors and workflow recipes
- [Security](SECURITY.md) - Security architecture and threat model
- [Use Cases](USE_CASES.md) - Detailed scenarios
- [SKILL.md](../SKILL.md) - Skill interface and command reference
- [ADR-001](ADR-001-repl-security-relaxation.md) - REPL security decisions
