# DeepScan Use Cases

> Reference guide for practical DeepScan usage scenarios.

## 1. Initialization Modes

### Full Mode (`init <path>`)

> **Size Guidance**: Best for projects under 5MB / 100 files.
> For larger projects, use `--lazy` or `--target` to avoid context bloat.
> DeepScan will warn if chunk count exceeds 100 and error at 500+.

| Scenario | Description |
|----------|-------------|
| **Small-to-medium project scan** | Up to ~100 files, <5MB total |
| **New team member onboarding** | Understand entire project structure |
| **Pre-release code review** | Full codebase quality verification |

### Lazy Mode (`--lazy`)
| Scenario | Description |
|----------|-------------|
| **Monorepo exploration** | Hundreds of packages, explore structure first |
| **Legacy system understanding** | 1M+ LOC, unknown entry points |
| **Bug tracking** | Progressive loading of related files only |

```bash
init . --lazy
exec -c "print(get_tree_view())"
exec -c "print(preview_dir('packages/auth'))"
exec -c "print(load_file('packages/auth/src/index.ts'))"
```

### Targeted Mode (`--target`)
| Scenario | Description |
|----------|-------------|
| **PR code review** | Analyze only changed 5-10 files |
| **Module security audit** | Deep review of `src/auth/` only |
| **Dependency impact analysis** | Track specific library usage |

```bash
init . --target src/api/users.py --target src/models/user.py --target tests/test_users.py
```

---

## 2. Scout Functions

| Function | Scenario |
|----------|----------|
| `peek_head(5000)` | **First impression** - entry points, import patterns |
| `peek_tail(5000)` | **Recent code** - latest changes in time-sorted files |
| `grep('TODO\|FIXME')` | **Tech debt inventory** - collect all TODO items |
| `grep('password\|secret\|api_key')` | **Sensitive info scan** - detect hardcoded secrets |
| `grep_file(pattern, file)` | **Lazy mode search** - targeted file search without full load |

**Example: Tech Debt Audit**
```bash
init ./src
exec -c "todos = grep('TODO|FIXME|HACK|XXX', max_matches=200)"
exec -c "print(f'Tech debt: {len(todos)} items')"
```

---

## 3. Chunking Strategies

| Scenario | Recommended Settings |
|----------|----------------------|
| **General code analysis** | `size=150000, overlap=0` |
| **Data flow tracing** (continuity needed) | `size=150000, overlap=10000` |
| **Large log analysis** | `size=200000, overlap=5000` |

### Adaptive Chunking (`--adaptive`)
| Scenario | Why |
|----------|-----|
| **Mixed projects** | Python + JSON config + Markdown docs |
| **Microservices** | Different languages/configs per service |

---

## 4. Parallel Processing (MAP)

| Scenario | Approach |
|----------|----------|
| **Fast full scan** | `map` (5 parallel agents) |
| **Complex analysis** | `map --escalate` (sonnet on quality issues) |
| **Manual control** | `map --instructions` → Task tool |

**Example: Large-scale Security Audit**
```bash
init ./src -q "Find SQL injection, XSS, credential leaks"
exec -c "paths = write_chunks(size=100000); print(f'{len(paths)} chunks')"
map --escalate
```

---

## 5. Result Aggregation (REDUCE)

| Feature | Scenario |
|---------|----------|
| **Deduplication** | Same pattern found in multiple files → dedupe |
| **Contradiction Detection** | Chunk A: "safe" vs Chunk B: "vulnerable" → flag |
| **Source Tracking** | Exact file:line evidence for audit reports |

---

## 6. Session Management

| Command | Scenario |
|---------|----------|
| `list` | **Multiple projects** - check active sessions |
| `resume` | **Network recovery** - continue 50% completed analysis |
| `abort` | **Wrong query** - delete and restart |
| `clean --older-than 7` | **Disk cleanup** - remove week-old cache |
| `progress` | **Long analysis** - monitor completion % |

---

## 7. Analysis Focus Areas

> **Note**: Specialized agent types are fully implemented (Phase 8).
> Use the `--agent-type` flag or the `-q` query parameter to focus your analysis.

| Focus Area | Agent Type Flag | Query Example |
|------------|-----------------|---------------|
| **Security** | `--agent-type security` | `-q "Find SQL injection, XSS, credential leaks"` |
| **Architecture** | `--agent-type architecture` | `-q "Find layer violations, circular dependencies"` |
| **Performance** | `--agent-type performance` | `-q "Find N+1 queries, nested loops, memory leaks"` |

**Example: Security-focused Analysis**
```bash
init ./src --agent-type security -q "Identify vulnerabilities: SQL injection, XSS, hardcoded secrets"
map --escalate
```

---

## 8. Incremental Analysis

| Scenario | Benefit |
|----------|---------|
| **CI/CD pipeline** | PR changes only → reduced build time |
| **Daily security scan** | Changed files since yesterday only |
| **Large refactoring** | Re-analyze affected chunks only |

**Performance**: 3-10x faster for typical incremental changes (5-10% files modified)

---

## 9. End-to-End Scenarios

### Scenario A: Legacy System Handover
```bash
# 1. Structure exploration (Lazy)
init ./legacy-system --lazy
exec -c "print(get_tree_view())"

# 2. Core module identification
exec -c "print(preview_dir('src/core'))"

# 3. Full analysis
init ./legacy-system --adaptive -q "Document architecture, identify dead code, find security issues"
map --escalate

# 4. Export results
export-results legacy_analysis.json
```

### Scenario B: Security Incident Response
```bash
# 1. Quick sensitive info scan
init ./src -q "Find hardcoded credentials, API keys, tokens"
exec -c "results = grep('password|secret|api_key|bearer', max_matches=100)"

# 2. Deep analysis of suspect areas
init ./src --target src/auth/ --target src/api/ -q "Find auth bypass, credential leaks, injection attacks"
map --escalate

# 3. Evidence collection
export-results incident_evidence.json
```

### Scenario C: Migration Impact Analysis
```bash
# 1. Library usage discovery
init ./src -q "Find all usages of deprecated-lib and migration impact"
exec -c "usages = grep('from deprecated_lib|import deprecated_lib', max_matches=500)"

# 2. Dependency chain tracing
map

# 3. Migration plan
export-results migration_plan.json
```

---

## DeepScan vs Simple Tools

| Situation | Recommended Tool |
|-----------|------------------|
| Single file pattern search | `Grep` directly |
| File listing | `Glob` directly |
| Reading 1-3 files | `Read` directly |
| **10+ file analysis** | DeepScan |
| **1MB+ context** | DeepScan |
| **Multi-hop reasoning** | DeepScan |
| **Evidence-based reports** | DeepScan |

---

## 10. Custom Ignore Patterns (`.deepscanignore`)

> **New Feature (Issue #7)**: Project-specific ignore patterns.

Create a `.deepscanignore` file in your project root:

```
# .deepscanignore
# Lines starting with # are comments

# Directory names (matched against any path component)
generated
.coverage
htmlcov

# Glob patterns (with * or ?)
*.min.js
*.map
data/fixtures/*.json
```

**Pattern Types**:
- **Directory names** (no wildcards): Matched against any path component
- **Glob patterns** (with `*` or `?`): Matched against relative file paths

---

## 11. MAP Phase Pagination

> **New Feature (Issue #5)**: Handle large chunk counts efficiently.

```bash
# Show first batch with 5 chunks (default)
map --instructions

# Show specific batch
map --instructions --batch 3

# Show more chunks per batch
map --instructions --limit 10

# Save all instructions to file
map --instructions --output prompts.md
```

**Flags**:
- `--output, -o FILE`: Write instructions to file instead of stdout
- `--batch N`: Show specific batch only (1-indexed)
- `--limit N`: Max chunks to show (default: 5)
