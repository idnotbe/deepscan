# Phase 1: Documentation Analysis

> Generated: 2026-02-16
> Analyst: doc-scanner agent

---

## 1. Document-by-Document Analysis

### 1.1 CLAUDE.md (Project Instructions)

**Path**: `/home/idnotbe/projects/deepscan/CLAUDE.md`
**Purpose**: Developer-facing project instructions loaded into Claude Code sessions. Defines repository layout, testing status, security invariants, and pointers to other docs.

**Features Documented**:
- Repository layout (4 top-level paths)
- Testing status (explicitly states no tests exist)
- Security-critical module list with line-number references
- Known security gaps
- Security invariant policy (3-step change process)
- Policy enforcement locations with line numbers

**Modules Referenced**:
| Module | Context |
|--------|---------|
| `repl_executor.py` | Sandboxed eval/exec, timeout, zombie thread DoS, Windows resource fallback |
| `deepscan_engine.py` | Forbidden patterns (lines 344-367), AST whitelist (lines 368-460), attribute blocking |
| `constants.py` | SAFE_BUILTINS allowlist (lines 109-148) |
| `state_manager.py` | `_safe_write()` path containment (lines 381-398) |
| `walker.py` | `follow_symlinks=False`, max depth |
| `ast_chunker.py` | Project-root enforcement (lines 400-420) |

**Modules NOT Referenced**: `__init__.py`, `aggregator.py`, `cancellation.py`, `checkpoint.py`, `error_codes.py`, `grep_utils.py`, `helpers.py`, `incremental.py`, `models.py`, `progress.py`, `subagent_prompt.py` (11 of 17 modules missing)

**Config Options Documented**: None directly (points to SKILL.md)

**User Workflows**: None (development-focused, not user-facing)

**Error Handling Guidance**: None

**Security Documentation**:
- Explicit "untrusted input" principle for REPL code, file paths, chunk contents
- 3-step change process for sandbox policy modifications
- Line-number references for all security enforcement points
- Known gaps: unchecked SECURITY.md checklist item, zombie thread DoS, SAFE_BUILTINS introspection risk, no Windows testing

**Installation/Setup**: None (developer doc, not install doc)

**API/Interface Documentation**: None

**Cross-References**:
- README.md (Plugin overview)
- SECURITY.md (Threat model)
- ARCHITECTURE.md (System design)
- TEST-PLAN.md (Test plan)

**Gaps/TODO Markers**:
- "CRITICAL: No tests exist yet" -- prominent notice
- Unchecked checklist item reference in SECURITY.md line 278

**Staleness Indicators**:
- Line number references (344-367, 368-460, 109-148, 381-398, 400-420, 239-305, 82-94) are fragile and will break on code changes
- States "17 modules" -- must be kept in sync with actual file count

---

### 1.2 README.md (Root)

**Path**: `/home/idnotbe/projects/deepscan/README.md`
**Purpose**: Public-facing README. Plugin overview, installation, usage quickstart, feature summary, and documentation index.

**Features Documented**:
- Map-reduce pattern (4-step: load, chunk, map, reduce)
- When to use / when NOT to use
- Installation (plugin add + git clone)
- Usage quickstart (single command)
- Specialized agents (4 types: general, security, architecture, performance)
- Key features list (6 items: checkpoints, incremental, progress streaming, deduplication, model escalation, sandboxed REPL)
- Testing status (no tests, with planned commands)
- License (MIT)

**Modules Referenced**:
| Module | Context |
|--------|---------|
| `repl_executor.py` | Sandboxed eval/exec, timeout |
| `deepscan_engine.py` | Forbidden patterns, AST whitelist, attribute blocking |
| `constants.py` | SAFE_BUILTINS |
| `state_manager.py` | Path containment |
| `walker.py` | Symlink safety |
| `ast_chunker.py` | Project-root enforcement |

**Config Options Documented**: None directly

**User Workflows**: Basic quickstart only (`/deepscan init ./src -q "query"`)

**Error Handling Guidance**: None

**Security Documentation**: Mentions security-critical components needing tests

**Installation/Setup**:
- `claude plugin add idnotbe/deepscan`
- `git clone https://github.com/idnotbe/deepscan.git`

**API/Interface Documentation**: Points to SKILL.md for full command reference

**Cross-References**:
- SKILL.md (command reference)
- ARCHITECTURE.md
- SECURITY.md
- USE_CASES.md
- TEST-PLAN.md
- CLAUDE.md
- LICENSE

**Gaps/TODO Markers**:
- "No tests exist yet" -- critical gap notice

**Staleness Indicators**:
- Coverage command references `--cov=.claude/skills/deepscan/scripts` -- path could change
- GitHub URL `https://github.com/idnotbe/deepscan` -- must exist for installation

---

### 1.3 TEST-PLAN.md

**Path**: `/home/idnotbe/projects/deepscan/TEST-PLAN.md`
**Purpose**: Prioritized test plan organized by security criticality (P0/P1/P2). Defines specific test vectors and target code locations.

**Features Documented**:
- P0 (5 test suites): REPL sandbox escape, SAFE_BUILTINS introspection chains, path traversal, zombie thread DoS, forbidden pattern regex bypass
- P1 (4 test suites): Walker symlink safety, AST chunker robustness, AST whitelist relaxation, CI/CD setup
- P2 (4 test suites): State/checkpoint integrity, aggregator deduplication, error code/progress tests, resource limit cross-platform
- Test infrastructure requirements (directory structure, conftest, pyproject.toml)

**Modules Referenced**:
| Module | Lines Referenced | Test Category |
|--------|-----------------|---------------|
| `repl_executor.py` | 105-117, 239-305, 82-94 | P0 (sandbox escape, zombie threads), P2 (resource limits) |
| `constants.py` | 109-148 | P0 (SAFE_BUILTINS introspection) |
| `deepscan_engine.py` | 344-367, 380-462, 511-516 | P0 (forbidden patterns), P1 (AST whitelist) |
| `state_manager.py` | 381-398 | P0 (path traversal) |
| `checkpoint.py` | 96-115 | P0 (path traversal), P2 (integrity) |
| `ast_chunker.py` | 400-420 | P0 (path traversal), P1 (robustness) |
| `walker.py` | 200-210 | P1 (symlink safety) |
| `aggregator.py` | full module | P2 (deduplication) |
| `error_codes.py` | full module | P2 (error codes) |
| `progress.py` | full module | P2 (progress streaming) |

**Modules NOT Referenced**: `__init__.py`, `cancellation.py`, `grep_utils.py`, `helpers.py`, `incremental.py`, `models.py`, `subagent_prompt.py` (7 of 17 modules have no test plan)

**Config Options Documented**: None

**User Workflows**: None (test development guidance)

**Error Handling Guidance**: Error code mapping tests mentioned in P2

**Security Documentation**: Extensive -- specific attack vectors, bypass techniques, and test payloads for each security layer

**Installation/Setup**: Test infrastructure setup (directory structure, fixtures, dependencies)

**API/Interface Documentation**: None

**Cross-References**:
- SECURITY.md
- Based on: audit-deepscan.md, v1-security-review.md
- Cross-validated with: Codex 5.3, vibe-check skill

**Gaps/TODO Markers**:
- Entire plan is unimplemented (0 tests exist)

**Staleness Indicators**:
- Created: 2026-02-14
- Line number references throughout (fragile)
- References "audit-deepscan.md" and "v1-security-review.md" which are not in the repo

---

### 1.4 plugin.json (Plugin Manifest)

**Path**: `/home/idnotbe/projects/deepscan/.claude-plugin/plugin.json`
**Purpose**: Claude Code plugin registration manifest. Defines plugin metadata and skill locations.

**Features Documented**:
- Plugin name: "deepscan"
- Version: 0.1.0
- Description (concise)
- Author: idnotbe
- Skills path: `./.claude/skills/deepscan`
- Keywords: analysis, security-audit, architecture, multi-file, deep-scan

**Modules Referenced**: None directly

**Config Options Documented**: None (manifest-level config only)

**User Workflows**: None

**Error Handling Guidance**: None

**Security Documentation**: None

**Installation/Setup**: Implicitly defines the plugin structure

**API/Interface Documentation**: Plugin registration schema

**Cross-References**:
- Homepage/repository: https://github.com/idnotbe/deepscan

**Gaps/TODO Markers**: None

**Staleness Indicators**:
- Version 0.1.0 vs Skill README claiming "Version 2.0.0 (Phase 7)" -- VERSION MISMATCH

---

### 1.5 SKILL.md (Skill Trigger/Command Reference)

**Path**: `/home/idnotbe/projects/deepscan/.claude/skills/deepscan/SKILL.md`
**Purpose**: Claude Code skill definition. Contains YAML frontmatter (triggers, allowed tools) and comprehensive command reference.

**Features Documented**:
- Trigger phrases (10 triggers)
- Allowed tools (7: Read, Write, Edit, Bash, Task, Grep, Glob)
- Quick reference table (Full, Lazy, Targeted modes)
- Core workflow (6 steps: Init, Scout, Chunk, MAP, REDUCE, Session Management)
- Helper functions (full table with 14 functions)
- Lazy mode helpers (4 additional functions)
- Specialized agents (4 types)
- Result recording format (JSON schema)
- Configuration settings (5 settings with defaults)
- Model escalation details
- Key features summary
- Security summary (4 points)
- Troubleshooting table (4 common errors)

**Modules Referenced**: None by filename (references `deepscan_engine.py` indirectly via CLI commands)

**Config Options Documented**:
| Setting | Default | Range/Notes |
|---------|---------|-------------|
| `chunk_size` | 150000 | 50K-300K |
| `chunk_overlap` | 0 | -- |
| `max_parallel_agents` | 5 | -- |
| `timeout_seconds` | 300 | -- |
| `enable_escalation` | True | -- |

**User Workflows**:
- Full init -> scout -> chunk -> map -> reduce -> export
- Lazy mode exploration
- Targeted file analysis
- Session management (list, resume, abort, clean)

**Error Handling Guidance**:
| Error | Solution |
|-------|----------|
| "No state found" | Run init first |
| "Forbidden pattern" | Use allowed helpers |
| "File too large" | Files >10MB skipped |
| Windows Unicode | Set PYTHONIOENCODING |

**Security Documentation**:
- JSON-only serialization
- Sandboxed REPL (restricted builtins, AST validation)
- File limits (10MB/file, 50MB total)
- Path traversal protection

**Installation/Setup**: CLI command format (`poetry run python .claude/skills/deepscan/scripts/deepscan_engine.py ...`)

**API/Interface Documentation**: Full CLI command reference + REPL helper function API

**Cross-References**:
- docs/USE_CASES.md
- docs/ARCHITECTURE.md
- docs/SECURITY.md

**Gaps/TODO Markers**: None explicit

**Staleness Indicators**:
- CLI command format uses `poetry run python ...` but no pyproject.toml in root for poetry

---

### 1.6 Skill README.md

**Path**: `/home/idnotbe/projects/deepscan/.claude/skills/deepscan/README.md`
**Purpose**: Comprehensive technical README. Most detailed single document in the project -- covers design rationale, full workflow, helper functions, project layout, security, limitations, development standards, and roadmap.

**Features Documented**:
- Design goals and rationale (context rot problem)
- Phase 7 features (3 categories: Core, Parallel Processing, Advanced)
- Model quality trade-offs (Haiku vs Sonnet comparison)
- Quick start workflow (5 steps)
- Complete workflow example with expected CLI outputs (5 steps)
- Session resumption with expected outputs
- Session conflict handling
- Session cleanup
- Helper functions (full table with 15 functions, args, return types)
- Project layout (file tree with LOC counts)
- Security: Sandboxed REPL, File Access, Serialization
- Known limitations (5: CLI vs Claude Code, Model escalation budget, Platform paths, Execution modes, REPL syntax restrictions)
- Development standards (type checking, line length, testing, security scanning)
- File metrics (LOC per module, total ~6370)
- Roadmap (Phases 1-7 completed, Phase 8 future)
- Contributing guidelines (TDD protocol)

**Modules Referenced in Project Layout**:
| Module | LOC (claimed) |
|--------|---------------|
| `deepscan_engine.py` | ~2500 |
| `subagent_prompt.py` | ~400 |
| `aggregator.py` | ~600 |
| `checkpoint.py` | ~280 |
| `cancellation.py` | ~460 |
| `incremental.py` | ~530 |
| `error_codes.py` | ~450 |
| `ast_chunker.py` | ~1000 |
| `models.py` | ~150 |

**Modules NOT Listed in Layout**: `__init__.py`, `constants.py`, `walker.py`, `repl_executor.py`, `state_manager.py`, `progress.py`, `helpers.py`, `grep_utils.py` (8 of 17 modules missing from file tree)

**Config Options Documented**: Indirect (via helper function args and CLI flags)

**User Workflows**:
- Init -> Explore -> Chunk -> Status -> Export (quick start)
- Full init -> chunk -> map -> progress -> reduce -> export (complete)
- Resume workflow
- Session conflict resolution
- Cleanup workflow

**Error Handling Guidance**:
- Session conflict handling with --force/resume/abort options
- CLI mode vs Claude Code limitation

**Security Documentation**:
- Restricted builtins (no __import__, eval, exec, open, os)
- AST validation
- Pattern blocking
- Write isolation (only deepscan cache writable)
- Size limits (10MB/file, 50MB total)
- Path traversal protection
- JSON only (no pickle)
- Pydantic validation

**Installation/Setup**: CLI command format with poetry

**API/Interface Documentation**:
- Full helper function reference (15 functions with args, types, descriptions)
- CLI command reference via examples
- Result recording JSON format

**Cross-References**:
- docs/ARCHITECTURE.md
- docs/SECURITY.md
- docs/ADR-001-repl-security-relaxation.md
- SKILL.md
- ERROR_REPORT_DEEPSCAN_SKILLS.md (referenced but not found in repo)

**Gaps/TODO Markers**:
- "Phase 8 (Future): Semantic Chunking" -- planned but not implemented
- "Unit tests (when implemented)" -- acknowledges missing tests

**Staleness Indicators**:
- Version "2.0.0 (Phase 7)" vs plugin.json "0.1.0" -- MISMATCH
- File layout lists 9 modules but 17 exist -- INCOMPLETE
- Total LOC "~6370" likely outdated
- References ERROR_REPORT_DEEPSCAN_SKILLS.md which doesn't exist in repo
- Phase 8 "AST-based chunking" is listed as future but `ast_chunker.py` already exists (1000 LOC)
- "Phase 8" is referenced for `--agent-type` flag being "fully implemented" but earlier sections say "Phase 7"

---

### 1.7 ARCHITECTURE.md

**Path**: `/home/idnotbe/projects/deepscan/.claude/skills/deepscan/docs/ARCHITECTURE.md`
**Purpose**: System architecture documentation for contributors. Covers design goals, component design, workflow phases, data models, file structure, extension points, and performance characteristics.

**Features Documented**:
- Design goals (context rot problem, solution approach)
- Core principles (4: precision, evidence, resumable, secure)
- High-level architecture diagram (ASCII art)
- Component design (5 components): SKILL.md, REPL Engine, State Manager, Sub-Agent System, Aggregator
- Workflow phases (init -> scout -> chunk -> map -> reduce)
- Error recovery strategies (4 failure types)
- Data models (3 Pydantic schemas: ChunkInfo, Finding, ChunkResult)
- Session hash format
- File structure (directory tree)
- Extension points (3: custom agent types, chunking strategies, aggregation)
- Performance characteristics (4 metrics)

**Modules Referenced**:
| Module | Context |
|--------|---------|
| `deepscan_engine.py` | REPL engine, CLI |
| `aggregator.py` | Result aggregation, deduplication |
| `subagent_prompt.py` | Agent type instructions, prompt generation |
| `ast_chunker.py` | Semantic chunking |
| `models.py` | Pydantic schemas (indirectly) |

**Modules NOT Referenced**: `__init__.py`, `cancellation.py`, `checkpoint.py`, `constants.py`, `error_codes.py`, `grep_utils.py`, `helpers.py`, `incremental.py`, `progress.py`, `repl_executor.py`, `state_manager.py`, `walker.py` (12 of 17 modules not mentioned)

**Config Options Documented**: Indirect (similarity_threshold 0.7, confidence_weights, batch size 5)

**User Workflows**: Workflow phase diagram (init -> scout -> chunk -> map -> reduce)

**Error Handling Guidance**: Error recovery strategy table (4 failure types with strategies)

**Security Documentation**: Brief -- mentions "Sandboxed REPL with multi-layer defense", points to SECURITY.md

**Installation/Setup**: None

**API/Interface Documentation**:
- Pydantic data model schemas
- Extension point APIs (3)

**Cross-References**:
- SKILL.md
- SECURITY.md
- ADR-001

**Gaps/TODO Markers**: None explicit

**Staleness Indicators**:
- File structure lists only 9 modules (8 missing)
- Line reference "line 1431" for CLI choices in deepscan_engine.py -- fragile
- Claims "--agent-type CLI flag is fully implemented (Phase 8)" but Skill README says Phase 7 is current

---

### 1.8 SECURITY.md

**Path**: `/home/idnotbe/projects/deepscan/.claude/skills/deepscan/docs/SECURITY.md`
**Purpose**: Security architecture documentation. Covers threat model, defense layers, REPL security, file access, prompt injection defense, state file integrity, session isolation, and DoS protections.

**Features Documented**:
- Threat model (6 attack vectors with risk levels)
- Trust boundary diagram
- Defense-in-depth architecture (5 layers)
- REPL security model: allowed vs blocked operations
- Why getattr is dangerous (with code example)
- Known limitations (ThreadPoolExecutor timeout, Memory DoS)
- File access security (write isolation, path traversal, size limits)
- Prompt injection defense (XML boundary structure)
- State file integrity (JSON-only, optional HMAC)
- Session isolation (hash-based namespacing)
- DoS protections (5 attack types)
- ReDoS prevention (with code example)
- Security checklist for contributors (7 items)
- ADR references

**Modules Referenced**: None by filename (describes security patterns implemented across multiple modules)

**Config Options Documented**:
- ALLOWED_WRITE_PATHS
- File size limits (10MB, 50MB, 1GB GC)
- Timeout (5 seconds)
- Symlink max depth (10)
- Overlap ratio limit (50% of chunk size)
- Regex pattern max length (100 chars), max wildcards (3)
- Grep timeout (1 second)

**User Workflows**: None (security reference doc)

**Error Handling Guidance**: None directly (describes security error conditions)

**Security Documentation**: THIS IS THE PRIMARY SECURITY DOC
- Comprehensive threat model
- Defense-in-depth with 5 layers
- Code examples for attacks and defenses
- Known limitations clearly documented
- Contributor security checklist

**Installation/Setup**: None

**API/Interface Documentation**:
- safe_write() pseudo-code
- HMAC signature scheme
- grep() with ReDoS protection pseudo-code

**Cross-References**:
- ARCHITECTURE.md
- SKILL.md
- ADR-001
- External: HackTricks Python sandbox bypass guide

**Gaps/TODO Markers**:
- `[ ] Test for path traversal with .. and symlinks` (line 278) -- UNCHECKED CHECKLIST ITEM
- `[ ] Never add getattr, setattr, format to SAFE_BUILTINS` (line 273) -- checklist format
- Several checklist items are unchecked (all 7 items on lines 273-279)

**Staleness Indicators**:
- HMAC signing described as "Optional" -- unclear if implemented
- Code examples may not match actual implementation (pseudo-code style)
- No version or date

---

### 1.9 USE_CASES.md

**Path**: `/home/idnotbe/projects/deepscan/.claude/skills/deepscan/docs/USE_CASES.md`
**Purpose**: Practical usage scenarios and workflow examples. Organized by feature area with concrete commands.

**Features Documented**:
- 3 initialization modes (Full, Lazy, Targeted) with scenario tables
- Scout functions (5 functions with scenarios)
- Chunking strategies (3 scenarios with settings)
- Adaptive chunking
- Parallel processing (3 approaches)
- Result aggregation (3 features)
- Session management (5 commands)
- Analysis focus areas with --agent-type flag
- Incremental analysis (3 scenarios)
- 3 end-to-end scenarios (Legacy Handover, Security Incident, Migration)
- DeepScan vs Simple Tools comparison
- Custom ignore patterns (.deepscanignore) -- NEW FEATURE
- MAP phase pagination -- NEW FEATURE

**Modules Referenced**: None by filename

**Config Options Documented**:
- Chunk sizes for different scenarios (100K, 150K, 200K)
- Overlap settings (0, 5000, 10000)
- --agent-type flag values
- .deepscanignore pattern syntax
- --batch, --limit, --output flags for MAP pagination

**User Workflows**:
- Tech debt audit (init -> grep -> count)
- Large-scale security audit (init -> chunk -> map --escalate)
- Legacy system handover (lazy -> explore -> full -> map -> export)
- Security incident response (quick scan -> deep analysis -> evidence)
- Migration impact analysis (discovery -> trace -> plan)

**Error Handling Guidance**: None

**Security Documentation**: Minimal (mentions security audit as a use case)

**Installation/Setup**: None

**API/Interface Documentation**: CLI command examples

**Cross-References**: None to other docs

**Gaps/TODO Markers**:
- "New Feature (Issue #7)" -- .deepscanignore
- "New Feature (Issue #5)" -- MAP pagination
- Neither feature's implementation status is confirmed

**Staleness Indicators**:
- "Phase 8" claimed for --agent-type in Section 7 note
- .deepscanignore feature documented but no .deepscanignore file exists in repo
- Issue #7 and Issue #5 references -- status unknown

---

### 1.10 ADR-001-repl-security-relaxation.md

**Path**: `/home/idnotbe/projects/deepscan/.claude/skills/deepscan/docs/ADR-001-repl-security-relaxation.md`
**Purpose**: Architecture Decision Record for relaxing REPL security restrictions. Written in Korean. Documents which AST nodes and builtins were allowed/blocked, with security rationale.

**Features Documented**:
- Context: original restrictive AST whitelist (21 nodes)
- Decision: 9 new AST nodes allowed, 5 new builtins allowed
- Still-blocked items with reasons (5 categories)
- Multi-layer defense architecture recap (5 layers)
- DoS defense for new features
- Consequences (positive, negative, neutral)

**Modules Referenced**: None by filename (describes security policy)

**Config Options Documented**: None

**User Workflows**: None

**Error Handling Guidance**: None

**Security Documentation**: Detailed
- 9 newly allowed AST nodes with justification
- 5 newly allowed builtins with justification
- 7 still-blocked code execution patterns with reasons
- 2 blocked module system nodes
- 3 blocked function/class definition nodes
- 2 blocked scope escape nodes
- 6 blocked dunder attributes with escape chain example
- Multi-layer defense diagram
- DoS defense for comprehensions

**Installation/Setup**: None

**API/Interface Documentation**: None

**Cross-References**:
- SECURITY.md (Section 3.3)
- External: Python AST docs, HackTricks Python jail escape, OWASP ReDoS

**Gaps/TODO Markers**: None

**Staleness Indicators**:
- Date: 2026-01-21
- "Memory limit: currently unimplemented, Phase 8 planned" -- consistent with other docs
- Written in Korean -- may be inaccessible to some contributors

---

## 2. Documentation Coverage Matrix

### 2.1 Module Coverage (Which modules are documented where?)

| Module | CLAUDE.md | README | TEST-PLAN | SKILL.md | Skill README | ARCH | SECURITY | USE_CASES | ADR-001 |
|--------|-----------|--------|-----------|----------|-------------|------|----------|-----------|---------|
| `__init__.py` | - | - | - | - | - | - | - | - | - |
| `aggregator.py` | - | - | P2 | - | layout | yes | - | - | - |
| `ast_chunker.py` | yes (security) | yes | P0/P1 | - | layout | yes | - | - | - |
| `cancellation.py` | - | - | - | - | layout | - | - | - | - |
| `checkpoint.py` | - | - | P0/P2 | - | layout | - | - | - | - |
| `constants.py` | yes (security) | yes | P0 | - | - | - | - | - | - |
| `deepscan_engine.py` | yes (security) | yes | P0/P1 | indirect | layout | yes | - | - | - |
| `error_codes.py` | - | - | P2 | - | layout | - | - | - | - |
| `grep_utils.py` | - | - | - | - | - | - | - | - | - |
| `helpers.py` | - | - | - | - | - | - | - | - | - |
| `incremental.py` | - | - | - | - | layout | - | - | - | - |
| `models.py` | - | - | - | - | layout | indirect | - | - | - |
| `progress.py` | - | - | P2 | - | - | - | - | - | - |
| `repl_executor.py` | yes (security) | yes | P0/P2 | - | - | - | - | - | - |
| `state_manager.py` | yes (security) | yes | P0/P2 | - | - | - | - | - | - |
| `subagent_prompt.py` | - | - | - | - | layout | yes | - | - | - |
| `walker.py` | yes (security) | yes | P1 | - | - | - | - | - | - |

**Coverage Summary**:
- **Fully undocumented modules** (appear in 0 docs): `__init__.py`, `grep_utils.py`, `helpers.py`
- **Barely documented** (1 doc only): `cancellation.py` (layout only), `incremental.py` (layout only), `models.py` (layout only)
- **Well documented** (3+ docs): `deepscan_engine.py`, `ast_chunker.py`, `constants.py`, `repl_executor.py`, `state_manager.py`, `walker.py`

### 2.2 Feature Coverage (Which features are documented where?)

| Feature | SKILL.md | Skill README | ARCH | USE_CASES | SECURITY | README |
|---------|----------|-------------|------|-----------|----------|--------|
| Init modes (full/lazy/targeted) | yes | yes | yes | yes | - | brief |
| Scout/peek/grep helpers | yes | yes | - | yes | - | - |
| Chunking (fixed/adaptive/semantic) | yes | yes | yes | yes | - | brief |
| MAP parallel processing | yes | yes | yes | yes | - | brief |
| REDUCE aggregation | brief | brief | yes | yes | - | brief |
| Model escalation | yes | yes | yes | brief | - | brief |
| Checkpoints/resume | yes | yes | yes | yes | - | brief |
| Progress streaming | yes | yes | - | yes | - | brief |
| Incremental analysis | brief | yes | - | yes | - | brief |
| Session management | yes | yes | - | yes | - | - |
| Sandboxed REPL | brief | yes | brief | - | yes | brief |
| Path traversal protection | brief | brief | - | - | yes | brief |
| Prompt injection defense | - | - | - | - | yes | - |
| State file integrity | - | - | - | - | yes | - |
| .deepscanignore | - | - | - | yes | - | - |
| MAP pagination | - | - | - | yes | - | - |
| --agent-type flag | brief | - | yes | yes | - | brief |
| Error codes system | - | - | - | - | - | - |
| Cancellation | - | - | - | - | - | - |
| Grep utilities | - | - | - | - | brief | - |
| REPL syntax restrictions | - | yes | - | - | - | - |

### 2.3 Configuration Coverage

| Config Parameter | Documented In | Default Value | Notes |
|-----------------|---------------|---------------|-------|
| `chunk_size` | SKILL.md | 150000 | Range: 50K-300K |
| `chunk_overlap` | SKILL.md | 0 | - |
| `max_parallel_agents` | SKILL.md | 5 | - |
| `timeout_seconds` | SKILL.md | 300 | SECURITY.md says 5s for REPL |
| `enable_escalation` | SKILL.md | True | - |
| Escalation budget (%) | Skill README | 15% | Max chunks |
| Escalation budget ($) | Skill README | $5 | Per session |
| File size limit | SECURITY.md, SKILL.md | 10MB | Per file |
| Total context limit | SECURITY.md, SKILL.md | 50MB | - |
| Session cache GC | SECURITY.md | 1GB | Total |
| Dedup threshold | Multiple | 0.7 | Jaccard similarity |
| Symlink max depth | SECURITY.md | 10 | - |
| Regex max length | SECURITY.md | 100 chars | - |
| Grep timeout | SECURITY.md | 1 second | ReDoS protection |
| write_chunks timeout | Skill README | auto (2s/MB) | Min 30s, max 120s |

**CONFLICT**: `timeout_seconds` is 300 in SKILL.md config table but REPL exec timeout is 5 seconds in SECURITY.md. These refer to different things (sub-agent timeout vs REPL timeout) but this is not made clear.

---

## 3. Cross-Document Consistency Issues

### 3.1 Version Conflicts
| Source | Version |
|--------|---------|
| `plugin.json` | 0.1.0 |
| Skill README header | 2.0.0 (Phase 7) |
| No other version references | -- |

**Verdict**: Major inconsistency. Plugin manifest says 0.1.0, README says 2.0.0.

### 3.2 Phase Conflicts
| Claim | Source |
|-------|--------|
| "Phase 7 Features" / "Version 2.0.0 (Phase 7)" | Skill README |
| "--agent-type CLI flag fully implemented (Phase 8)" | ARCHITECTURE.md Section 7.1, USE_CASES.md Section 7 |
| "Phase 8 (Future): Semantic Chunking" | Skill README Roadmap |
| `ast_chunker.py` exists (1000 LOC) | Actual codebase |

**Verdict**: Phase numbering is inconsistent. AST chunker is listed as future Phase 8 in the roadmap but already exists. --agent-type is claimed as Phase 8 in some docs but the current version is Phase 7.

### 3.3 Module Count / File Layout Inconsistencies
| Source | Modules Listed | Actual |
|--------|---------------|--------|
| CLAUDE.md | "17 modules" | 17 (correct) |
| Skill README file tree | 9 modules | 17 (missing 8) |
| ARCHITECTURE.md file tree | ~9 modules (with `...`) | 17 (incomplete) |

**Missing from Skill README layout**: `constants.py`, `walker.py`, `repl_executor.py`, `state_manager.py`, `progress.py`, `helpers.py`, `grep_utils.py`, `__init__.py`

### 3.4 Referenced-but-Missing Files
| Reference | Referenced In | Status |
|-----------|--------------|--------|
| `ERROR_REPORT_DEEPSCAN_SKILLS.md` | Skill README line 373 | NOT FOUND in repo |
| `audit-deepscan.md` | TEST-PLAN.md line 199 | NOT FOUND in repo |
| `v1-security-review.md` | TEST-PLAN.md line 199 | NOT FOUND in repo |
| `.deepscanignore` | USE_CASES.md Section 10 | NOT FOUND in repo (feature may be undocumented in code) |
| `pyproject.toml` | TEST-PLAN.md, Skill README | NOT FOUND in repo root |

### 3.5 Timeout Value Inconsistencies
| Context | Value | Source |
|---------|-------|--------|
| REPL exec default | 5 seconds | SECURITY.md, ADR-001 |
| Sub-agent timeout | 300 seconds | SKILL.md config table |
| write_chunks timeout | auto (2s/MB, 30-120s) | Skill README |
| Grep timeout | 1 second | SECURITY.md |

These are different things but the documentation does not clearly distinguish them. The SKILL.md config table `timeout_seconds: 300` could be confused with REPL timeout.

---

## 4. Gap Summary

### 4.1 Completely Undocumented Modules
These modules exist in the codebase but have zero documentation coverage:
1. **`grep_utils.py`** -- No mention in any document
2. **`helpers.py`** -- No mention in any document (helper functions are documented but this module is not referenced by name)
3. **`__init__.py`** -- Package init, typically doesn't need docs

### 4.2 Severely Under-documented Modules
These appear only in file layout listings:
1. **`cancellation.py`** (~460 LOC) -- Only mentioned in Skill README file tree
2. **`incremental.py`** (~530 LOC) -- Only mentioned in Skill README file tree
3. **`models.py`** (~150 LOC) -- Only mentioned in Skill README file tree

### 4.3 Features Documented but Possibly Not Implemented
1. **`.deepscanignore`** -- Documented in USE_CASES.md but no file exists in repo
2. **HMAC state file signing** -- Described in SECURITY.md as "Optional" but implementation status unknown
3. **`reduce` CLI command** -- Used in Skill README workflow examples but not in SKILL.md command reference

### 4.4 Missing Documentation Types
1. **No API reference** -- No module-level docstring documentation
2. **No changelog** -- Only ADR-001 has a changelog table
3. **No contributing guide** -- Skill README has brief TDD mention, no CONTRIBUTING.md
4. **No troubleshooting guide** -- SKILL.md has a 4-row table, no comprehensive troubleshooting
5. **No migration guide** -- For users upgrading between versions/phases
6. **No environment requirements** -- Python version, OS requirements, dependencies

### 4.5 Security Documentation Gaps
1. **SECURITY.md checklist items are ALL unchecked** (lines 273-279) -- unclear if these are "rules to follow" or "tests to implement"
2. **No security testing documentation** -- TEST-PLAN.md exists but is entirely unimplemented
3. **HMAC implementation status unclear** -- described as "Optional" in pseudo-code
4. **`resource` module fallback on Windows** -- mentioned as gap in CLAUDE.md but no docs describe the impact

### 4.6 Staleness Risks (Line Number References)
All of these line-number references will break on code changes:
| Document | Reference |
|----------|-----------|
| CLAUDE.md | deepscan_engine.py:344-367, 368-460 |
| CLAUDE.md | constants.py:109-148 |
| CLAUDE.md | state_manager.py:381-398 |
| CLAUDE.md | ast_chunker.py:400-420 |
| CLAUDE.md | repl_executor.py:239-305, 82-94 |
| TEST-PLAN.md | repl_executor.py:105-117, 239-305, 82-94 |
| TEST-PLAN.md | constants.py:109-148 |
| TEST-PLAN.md | deepscan_engine.py:344-367, 380-462, 511-516 |
| TEST-PLAN.md | state_manager.py:381-398 |
| TEST-PLAN.md | checkpoint.py:96-115 |
| TEST-PLAN.md | ast_chunker.py:400-420 |
| TEST-PLAN.md | walker.py:200-210 |
| ARCHITECTURE.md | deepscan_engine.py line 1431 |

---

## 5. Documentation Quality Assessment

| Document | Completeness | Accuracy | Freshness | Usability |
|----------|-------------|----------|-----------|-----------|
| CLAUDE.md | Medium | High (with caveats) | Recent | Good for devs |
| README.md (root) | Medium | Good | Recent | Good for users |
| TEST-PLAN.md | High (for scope) | Good | 2026-02-14 | Good for test devs |
| plugin.json | Complete (for type) | Version mismatch | Unknown | N/A |
| SKILL.md | High | Good | Good | Excellent |
| Skill README | High | Multiple inconsistencies | Mixed | Good but long |
| ARCHITECTURE.md | Medium | Phase confusion | Mixed | Good for architects |
| SECURITY.md | High | Good (pseudo-code) | No date | Excellent |
| USE_CASES.md | High | Good | Phase confusion | Excellent |
| ADR-001 | Complete | Good | 2026-01-21 | Good (Korean only) |

---

## 6. Key Findings for Gap Analyst

1. **17 modules exist, but most docs only reference 6-9** -- 8 modules have no documentation beyond file layout mentions
2. **Version mismatch** between plugin.json (0.1.0) and Skill README (2.0.0)
3. **Phase numbering is confused** -- Phase 7 vs Phase 8 claims for same features
4. **Line number references are pervasive and fragile** -- 13+ specific line ranges across 3 documents
5. **3 referenced files don't exist** in the repo (ERROR_REPORT, audit, v1-security-review)
6. **SECURITY.md checklist items are all unchecked** -- ambiguous purpose
7. **No tests, no CI, no pyproject.toml** -- all testing infrastructure is aspirational
8. **.deepscanignore documented but doesn't exist** -- feature status unclear
9. **`reduce` command appears in examples but not in SKILL.md command reference**
10. **ADR-001 is in Korean** -- accessibility concern for English-speaking contributors
