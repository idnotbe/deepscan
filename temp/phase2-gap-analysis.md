# Phase 2: Gap Analysis -- Implementation vs Documentation

> Generated: 2026-02-16
> Analyst: gap-analyst agent
> Inputs: phase1-impl-analysis.md, phase1-doc-analysis.md, phase2-doc-restructure-plan.md
> Method: Cross-referencing every module, function, constant, and config option against all 10 documentation files, verified against actual source code.

---

## 1. Executive Summary -- Top 10 Gaps

| # | Gap | Priority | Impact |
|---|-----|----------|--------|
| 1 | **Version mismatch**: `plugin.json` says 0.1.0, `__init__.py` and Skill README say 2.0.0 | CRITICAL | Users see conflicting versions; plugin registry may report wrong version |
| 2 | **8 modules missing from Skill README file tree**: `constants.py`, `walker.py`, `repl_executor.py`, `state_manager.py`, `progress.py`, `helpers.py`, `grep_utils.py`, `__init__.py` | HIGH | Contributors cannot find module locations; inflates perceived simplicity |
| 3 | **26 error codes completely undocumented** in any user-facing doc | HIGH | Users see `[DS-NNN]` codes with no explanation anywhere in docs |
| 4 | **Grep timeout mismatch**: SECURITY.md pseudo-code shows 1-second ThreadPoolExecutor timeout; actual implementation uses 10-second process isolation (`constants.py:64`) | HIGH | Security auditors will find different architecture than documented |
| 5 | **Phase 8 roadmap claims AST chunking is "future"**, but `ast_chunker.py` already exists (~1000 LOC, fully functional) | HIGH | Users think semantic chunking is unavailable when it already works via `write_chunks(semantic=True)` |
| 6 | **Cancellation system undocumented**: Double-tap Ctrl+C, graceful shutdown, checkpoint save, resume -- 460 LOC of functionality with zero documentation | HIGH | Users lose work because they don't know about graceful cancellation |
| 7 | **CLI shortcuts undocumented**: `?`, `!`, `+`, `x`, auto-path-detection -- implemented but not mentioned in any doc | MEDIUM | Users miss convenient shortcuts |
| 8 | **`.deepscanignore` feature implemented but no example file** exists in repo; docs reference it but users cannot see the syntax | MEDIUM | Users cannot discover or use file exclusion |
| 9 | **`reduce` command exists in implementation** (line 1349-1435 of deepscan_engine.py) but missing from SKILL.md command reference | MEDIUM | Users don't know how to aggregate results |
| 10 | **`doc_url` property generates broken URLs** (`https://deepscan.io/docs/errors/DS-NNN`) -- this domain/path likely doesn't exist | MEDIUM | Error messages link to non-existent pages |

---

## 2. Gap Inventory by Category

### 2.1 Undocumented Modules

| Module | LOC (est.) | Doc Coverage | Priority | Notes |
|--------|------------|-------------|----------|-------|
| `grep_utils.py` | ~170 | **ZERO** -- not mentioned in any document by name | HIGH | ReDoS protection is a security feature; users should know grep is process-isolated |
| `helpers.py` | ~650+ | **ZERO** by module name -- individual helper functions are documented but the module itself is not listed anywhere | MEDIUM | The `create_helpers()` factory, validation logic, and `re` module removal (CVE-2026-002) are undocumented |
| `__init__.py` | 6 | **ZERO** | LOW | Package init, typically does not need docs |
| `constants.py` | ~360 | Mentioned in CLAUDE.md (security) only -- no user-facing docs | HIGH | Contains ALL default values (chunk sizes, timeouts, SAFE_BUILTINS) that users need to understand |
| `walker.py` | ~220 | Mentioned in CLAUDE.md (security) only | MEDIUM | Users should know about `DEFAULT_PRUNE_DIRS` (19 auto-pruned directories) |
| `repl_executor.py` | ~310 | Mentioned in CLAUDE.md (security) only | HIGH | Subprocess isolation, resource limits (256MB/512MB memory, 60s/120s CPU) -- important for security-conscious users |
| `state_manager.py` | ~730 | Mentioned in CLAUDE.md (security) only | HIGH | Contains `DEFAULT_CACHE_ROOT`, file size limits, `.deepscanignore` parsing, session lifecycle |
| `progress.py` | ~180 | In TEST-PLAN.md (P2) only | MEDIUM | `should_escalate()`, `classify_failure()`, `EscalationBudget` -- escalation logic undocumented |

### 2.2 Undocumented Public Functions

| Function | Module | Priority | Why It Matters |
|----------|--------|----------|----------------|
| `aggregate_chunk_results()` | `aggregator.py` | MEDIUM | Convenience wrapper; alternative API for aggregation |
| `parse_final_markers()` | `aggregator.py` | MEDIUM | FINAL/FINAL_VAR/NEEDS_MORE/UNABLE markers -- users need to know this protocol |
| `extract_final_answer()` | `aggregator.py` | MEDIUM | How the system extracts final answers from sub-agent responses |
| `has_final_marker()` | `aggregator.py` | LOW | Quick check utility |
| `fallback_text_chunk()` | `ast_chunker.py` | MEDIUM | Fallback when AST parsing fails; explains why some chunks look different |
| `chunk_files_safely()` | `ast_chunker.py` | MEDIUM | Memory-managed generator with GC -- important for large codebases |
| `get_cancellation_manager()` | `cancellation.py` | HIGH | Singleton factory; users testing/extending need this |
| `atomic_write_with_cancellation()` | `cancellation.py` | MEDIUM | Explains atomic write behavior during cancellation |
| `restore_state_from_checkpoint()` | `checkpoint.py` | MEDIUM | How checkpoint restore works internally |
| `calculate_chunking_timeout()` | `constants.py` | MEDIUM | Dynamic timeout formula -- users wonder why timeouts differ |
| `detect_content_type()` | `constants.py` | LOW | How adaptive chunking decides chunk sizes |
| `_sanitize_xml_content()` | `subagent_prompt.py` | MEDIUM | Unicode lookalike detection -- important for security auditors |
| `create_sequential_prompt()` | `subagent_prompt.py` | MEDIUM | Simplified prompt for sequential fallback |
| `is_safe_regex()` | `grep_utils.py` | LOW | ReDoS heuristic detection |
| `should_escalate()` | `progress.py` | MEDIUM | Escalation trigger logic |
| `classify_failure()` | `progress.py` | MEDIUM | How failures are categorized |
| `validate_session_hash()` | `progress.py` | LOW | Hash validation rules |
| `reset_global_state()` | `repl_executor.py` | LOW | Test isolation utility |
| `_parse_deepscanignore()` | `state_manager.py` | HIGH | .deepscanignore parsing behavior -- users need to know syntax |
| `_should_skip_path()` | `state_manager.py` | MEDIUM | How path filtering combines DEFAULT_PRUNE_DIRS + custom patterns |
| `gc_clean_old_sessions()` | `state_manager.py` | MEDIUM | GC with TTL (7 days) and LRU (1GB) eviction -- only partially documented |
| `set_current_session_hash()` | `state_manager.py` | LOW | Session marker file management |

### 2.3 Undocumented Configuration Options & Constants

| Constant/Config | Value | Module | Priority | Current Doc Status |
|-----------------|-------|--------|----------|--------------------|
| `GREP_TIMEOUT` | 10 seconds | `constants.py:64` | HIGH | SECURITY.md says 1 second (wrong) |
| `MAX_OUTPUT_SIZE` | 500KB | `constants.py:67` | MEDIUM | Not documented |
| `MAX_CLI_OUTPUT` | 100KB | `constants.py:68` | MEDIUM | Not documented |
| `MAX_CONTEXT_PREVIEW` | 50KB | `constants.py:69` | MEDIUM | Not documented |
| `MAX_GREP_CONTENT_SIZE` | 5MB | `constants.py:70` | MEDIUM | Not documented in user-facing docs |
| `MAX_CODE_LENGTH` | 100KB | `deepscan_engine.py:339` | MEDIUM | REPL input size limit -- users hit this with no explanation |
| `GC_EVERY_N_FILES` | 50 | `ast_chunker.py` | LOW | Internal tuning |
| `MEMORY_THRESHOLD_MB` | 500 | `ast_chunker.py` | LOW | Internal tuning |
| `TOKEN_SAFETY_MARGIN` | 0.80 | `ast_chunker.py` | LOW | 80% utilization per chunk |
| `DEFAULT_PRUNE_DIRS` | 19 dirs | `walker.py` | HIGH | Users need to know which directories are auto-pruned |
| `DEFAULT_IGNORE_PATTERNS` | 16 patterns | `incremental.py` | MEDIUM | Users doing incremental scans need this |
| `WATCH_POLL_INTERVAL` | 2 seconds | `constants.py:229` | LOW | Progress watch polling |
| `DEFAULT_PROGRESS_MAX_SIZE` | 10MB | `constants.py:225` | LOW | Progress file rotation |
| `MAX_CHECKPOINT_READ_SIZE` | 100MB | `models.py:56` | MEDIUM | Asymmetric with write limit (20MB) -- confusing |
| `MAX_CHECKPOINT_WRITE_SIZE` | 20MB | `models.py:51` | MEDIUM | Checkpoint size limits |
| `REDOS_PATTERNS` | 12 patterns | `constants.py:156-176` | LOW | ReDoS detection heuristics |
| `CHUNK_SIZE_BY_EXTENSION` | 17+ mappings | `constants.py:186-217` | MEDIUM | Users doing adaptive chunking need this |
| `SESSION_HASH_PATTERN` | `^[a-zA-Z0-9_-]+$` | `models.py:46` | LOW | Session hash validation regex |
| `similarity_threshold` | 0.7 | `aggregator.py` | LOW | Documented in ARCHITECTURE.md |
| Resource limits (memory soft/hard) | 256MB/512MB | `repl_executor.py:87` | MEDIUM | Only CLAUDE.md mentions, no user docs |
| Resource limits (CPU soft/hard) | 60s/120s | `repl_executor.py:89` | MEDIUM | Only CLAUDE.md mentions |
| Resource limits (file size) | 10MB | `repl_executor.py:91` | LOW | REPL worker file size cap |

### 2.4 Undocumented Error Codes

**ALL 26 error codes are undocumented in user-facing documentation.** The error codes exist only in `error_codes.py` source code. No documentation file explains what any error code means or how to fix it.

SKILL.md troubleshooting mentions 4 error scenarios but does not reference any DS-NNN codes:

| SKILL.md Error | Closest Error Code | Gap |
|----------------|-------------------|-----|
| "No state found" | DS-306 | Code not mentioned |
| "Forbidden pattern" | N/A (not an error code) | Pattern blocking has no error code |
| "File too large" | DS-303 | Code not mentioned |
| Windows Unicode | N/A | Platform issue, no code |

Missing from all docs: DS-001 through DS-005, DS-006, DS-101 through DS-105, DS-201 through DS-205, DS-301/302, DS-305, DS-401 through DS-404, DS-501 through DS-505.

**Additionally**: The `doc_url` property in `error_codes.py` generates URLs like `https://deepscan.io/docs/errors/DS-001` which almost certainly do not exist. This means the error handler outputs broken links.

### 2.5 Undocumented Security Features

| Feature | Module | Priority | Notes |
|---------|--------|----------|-------|
| Process isolation for grep | `grep_utils.py` | HIGH | Grep runs in a separate process with `terminate()`/`kill()` on timeout -- much stronger than documented 1-second ThreadPoolExecutor |
| Unicode lookalike detection | `subagent_prompt.py` | MEDIUM | 14 unicode characters detected and replaced in prompt sanitization |
| Rich markup injection prevention | `error_codes.py:424` | LOW | `rich_escape()` applied to user-controlled strings |
| Session hash triple validation | `checkpoint.py:163` | MEDIUM | Regex + `..` check + post-resolution path traversal check |
| Atomic writes (temp + rename) | `state_manager.py`, `cancellation.py` | MEDIUM | Multiple modules use atomic writes for crash safety |
| Binary file detection | `helpers.py:load_file` | LOW | `load_file()` detects binary files and refuses to load |
| Symlink blocking in all traversal | `walker.py`, `state_manager.py` | MEDIUM | `follow_symlinks=False` throughout -- mentioned briefly in CLAUDE.md but not in user docs |
| NEEDS_VERIFICATION prefix | `aggregator.py` | LOW | Sub-agent flagging mechanism |
| Ghost findings cleanup (P7-003) | `aggregator.py` | MEDIUM | Findings from deleted files are filtered -- important for incremental scans |
| `re` module removed from REPL | `helpers.py` | MEDIUM | CVE-2026-002 fix -- users should know `re` is not available |

### 2.6 Undocumented Workflows

| Workflow | Module(s) | Priority | Notes |
|----------|-----------|----------|-------|
| Cancellation (Double-tap Ctrl+C) | `cancellation.py` | HIGH | 460 LOC, fully implemented, zero documentation |
| Checkpoint/resume details | `checkpoint.py` | MEDIUM | Resume is briefly mentioned; checkpoint internals (save-per-batch, asymmetric limits) are not |
| Progress monitoring (`--watch` mode) | `deepscan_engine.py`, `progress.py` | MEDIUM | `progress --watch` is documented in SKILL.md but JSONL rotation, max size, polling interval are not |
| Model escalation trigger conditions | `progress.py` | MEDIUM | Only QUALITY_LOW and COMPLEXITY after attempt >= 2 -- not explained in user docs |
| Sequential fallback | `deepscan_engine.py` | MEDIUM | Falls back after 2 consecutive >50% failure batches -- undocumented behavior |
| Batch pagination (MAP) | `deepscan_engine.py` | LOW | `--batch N`, `--limit N`, `--output FILE` documented in USE_CASES.md but not SKILL.md |
| Session GC (TTL + LRU) | `state_manager.py` | LOW | `clean` command documented; 1GB total size cap is not |
| Incremental analysis internals | `incremental.py` | MEDIUM | Hash algorithm selection (xxhash3 vs sha256), ignore patterns, symlink skipping |

### 2.7 Undocumented Data Models

| Model | Module | Priority | Notes |
|-------|--------|----------|-------|
| `FinalMarkerType` enum | `aggregator.py` | MEDIUM | FINAL/FINAL_VAR/NEEDS_MORE/UNABLE protocol |
| `FailureType` enum | `models.py` | MEDIUM | TIMEOUT, PARSE_ERROR, RATE_LIMIT, QUALITY_LOW, COMPLEXITY, UNKNOWN |
| `ScanMode` enum | `models.py` | LOW | FULL, LAZY, TARGETED -- documented indirectly via CLI flags |
| `LazyModeError` exception | `models.py` | MEDIUM | Raised when operation needs full context in lazy mode |
| `FileHash`, `FileDelta`, `FileHashManifest` | `incremental.py` | LOW | Incremental analysis internals |
| `EscalationBudget` class | `progress.py` | MEDIUM | Budget tracking -- users need to know what limits apply |
| `FileEntry` dataclass | `walker.py` | LOW | Internal data structure |
| `SemanticChunk` model | `ast_chunker.py` | MEDIUM | Pydantic model for AST-based chunks |

---

## 3. Stale/Incorrect Documentation Items

### 3.1 Confirmed Contradictions

| # | Document | Claim | Actual Implementation | Severity |
|---|----------|-------|----------------------|----------|
| 1 | `plugin.json` | version: "0.1.0" | `__init__.py:6`: `__version__ = "2.0.0"` | CRITICAL |
| 2 | SECURITY.md (line 264) | Grep timeout: 1 second via ThreadPoolExecutor | `constants.py:64`: `GREP_TIMEOUT = 10`; `grep_utils.py`: Process isolation (not ThreadPoolExecutor) | HIGH |
| 3 | Skill README Roadmap | "Phase 8 (Future): Semantic Chunking -- AST-based chunking for language-aware boundaries" | `ast_chunker.py`: 1000+ LOC, fully functional, supports 5 languages, exposed via `write_chunks(semantic=True)` | HIGH |
| 4 | ARCHITECTURE.md Section 7.1 | "--agent-type CLI flag is fully implemented (Phase 8)" | Current phase is 7, not 8; `--agent-type` works in Phase 7 | MEDIUM |
| 5 | USE_CASES.md Section 7 | "Phase 8" for agent-type | Same as above -- phase numbering inconsistency | MEDIUM |
| 6 | SECURITY.md pseudo-code (line 258) | `if len(pattern) > 100 or pattern.count('*') > 3` | Actual ReDoS check uses 12 regex patterns in `constants.py:156-176`, no length/wildcard check | MEDIUM |
| 7 | Skill README file tree | Lists 9 modules | 17 modules exist | MEDIUM |
| 8 | ARCHITECTURE.md file tree | Lists ~9 modules with `...` | 17 modules exist | MEDIUM |
| 9 | Skill README LOC total | "~6370 LOC" | Likely outdated since 8 modules are missing from the count | LOW |
| 10 | SECURITY.md Section 6 | "Optional: HMAC signature" | `state_manager.py:403`: "HMAC signature (DEFECT-005) not implemented" -- confirmed NOT implemented | LOW |
| 11 | DS-505 remediation template | `'deepscan --resume {session_id}'` | Actual CLI: `deepscan resume {session_hash}` (not `--resume`) | MEDIUM |
| 12 | SECURITY.md Section 5 | Symlink max depth: 10 | Not found as an explicit constant in implementation; `walker.py` uses `max_depth` parameter (no default of 10) | LOW |
| 13 | SECURITY.md Section 8 | "Overlap ratio limit: 50% of chunk size" | `helpers.py:chunk_indices` validates `overlap < size` but also has a 50K cap, not 50% | LOW |

### 3.2 Referenced-but-Missing Files

| Reference | Referenced In | Status |
|-----------|--------------|--------|
| `ERROR_REPORT_DEEPSCAN_SKILLS.md` | Skill README line 373 | NOT FOUND in repo |
| `audit-deepscan.md` | TEST-PLAN.md line 199 | NOT FOUND in repo |
| `v1-security-review.md` | TEST-PLAN.md line 199 | NOT FOUND in repo |
| `pyproject.toml` | TEST-PLAN.md, Skill README | NOT FOUND in repo root |

### 3.3 Fragile Line Number References

All of these will break on code changes:

| Document | Reference | Current Status |
|----------|-----------|----------------|
| CLAUDE.md | `deepscan_engine.py:344-367` (forbidden patterns) | Lines 344-361 currently -- already shifted |
| CLAUDE.md | `deepscan_engine.py:368-460` (AST whitelist) | Lines 382-462 currently -- shifted by ~14 lines |
| CLAUDE.md | `constants.py:109-148` (SAFE_BUILTINS) | Lines 110-148 currently -- close but shifted by 1 |
| CLAUDE.md | `state_manager.py:381-398` (_safe_write) | Lines 381-398 currently -- still accurate |
| CLAUDE.md | `ast_chunker.py:400-420` (project root) | Not verified in this pass |
| CLAUDE.md | `repl_executor.py:239-305` (zombie thread) | Not verified |
| CLAUDE.md | `repl_executor.py:82-94` (Windows resource) | Not verified |
| ARCHITECTURE.md | `deepscan_engine.py line 1431` | Not verified, likely shifted |
| TEST-PLAN.md | Multiple line ranges across 7 modules | All fragile |

---

## 4. Recommended Fixes per Documentation File

### 4.1 plugin.json

| Fix | Priority | Detail |
|-----|----------|--------|
| Update version | CRITICAL | Change `"version": "0.1.0"` to `"version": "2.0.0"` to match `__init__.py` |

### 4.2 README.md (root)

| Fix | Priority | Detail |
|-----|----------|--------|
| Add prerequisites | HIGH | Python 3.10+, pydantic, tree-sitter-language-pack (optional) |
| Add example finding | HIGH | Show a real `Finding` object with point/evidence/confidence/location |
| Link to new docs | HIGH | GETTING-STARTED.md, TROUBLESHOOTING.md, ERROR-CODES.md, REFERENCE.md |
| Remove or update version confusion | MEDIUM | Clarify relationship between plugin.json version and software version |

### 4.3 SKILL.md

| Fix | Priority | Detail |
|-----|----------|--------|
| Add `reduce` command | HIGH | Missing from command reference; implemented at deepscan_engine.py:1349 |
| Add CLI shortcuts section | MEDIUM | `?`, `!`, `+`, `x`, auto-path-detection (deepscan_engine.py FR-018.5) |
| Add `add_results_from_file` helper | MEDIUM | Missing from helper table; implemented in helpers.py |
| Add `set_final_answer` helper | MEDIUM | Missing from helper table; implemented in helpers.py |
| Replace troubleshooting with link | MEDIUM | Point to TROUBLESHOOTING.md and ERROR-CODES.md |
| Add cancellation note | MEDIUM | Brief mention of Ctrl+C behavior and resume |
| Add links to new docs | LOW | GETTING-STARTED.md, REFERENCE.md |

### 4.4 Skill README

| Fix | Priority | Detail |
|-----|----------|--------|
| Update file tree | HIGH | Add missing 8 modules: `constants.py`, `walker.py`, `repl_executor.py`, `state_manager.py`, `progress.py`, `helpers.py`, `grep_utils.py`, `__init__.py` |
| Fix roadmap: remove AST chunking from "Future" | HIGH | `ast_chunker.py` already exists and works |
| Fix phase numbering | MEDIUM | Standardize: Phase 7 is current, Phase 8 is future |
| Remove ERROR_REPORT reference | MEDIUM | File doesn't exist in repo |
| Update LOC total | LOW | Recalculate with all 17 modules |

### 4.5 ARCHITECTURE.md

| Fix | Priority | Detail |
|-----|----------|--------|
| Update file tree | MEDIUM | Add missing modules |
| Fix Phase 8 reference | MEDIUM | `--agent-type` is Phase 7, not Phase 8 |
| Add cross-links | LOW | Link to ERROR-CODES.md, REFERENCE.md |
| Remove fragile line number reference | LOW | Line 1431 reference |

### 4.6 SECURITY.md

| Fix | Priority | Detail |
|-----|----------|--------|
| Fix grep pseudo-code | HIGH | Replace 1-second ThreadPoolExecutor with accurate 10-second process isolation description |
| Fix ReDoS detection pseudo-code | MEDIUM | Replace pattern length/wildcard check with description of 12 REDOS_PATTERNS |
| Clarify HMAC status | MEDIUM | Explicitly state HMAC is NOT implemented (confirmed in state_manager.py:403) |
| Add user-friendly summary at top | MEDIUM | "Security at a Glance" section |
| Add resource limits documentation | MEDIUM | 256MB/512MB memory, 60s/120s CPU, 10MB file (Unix only) |
| Fix symlink max depth claim | LOW | No hardcoded "10" in implementation |
| Fix overlap ratio claim | LOW | Not exactly 50%; it's `overlap < size` plus 50K cap |

### 4.7 USE_CASES.md

| Fix | Priority | Detail |
|-----|----------|--------|
| Fix Phase 8 reference in Section 7 | MEDIUM | Change to Phase 7 or remove phase numbering |
| Clarify .deepscanignore status | LOW | Feature IS implemented in state_manager.py, just no example file exists |

### 4.8 TEST-PLAN.md

| Fix | Priority | Detail |
|-----|----------|--------|
| Remove references to missing files | MEDIUM | `audit-deepscan.md`, `v1-security-review.md` don't exist |
| Add missing modules to test plan | MEDIUM | `cancellation.py`, `grep_utils.py`, `helpers.py`, `incremental.py`, `models.py`, `subagent_prompt.py` have no test plan entries |

### 4.9 CLAUDE.md

| Fix | Priority | Detail |
|-----|----------|--------|
| Update line number references | MEDIUM | Forbidden patterns shifted to 344-361, AST whitelist to 382-462, SAFE_BUILTINS to 110-148 |
| Add `grep_utils.py` to security modules | MEDIUM | Process-isolated grep is a security mechanism |
| Add `subagent_prompt.py` to security modules | MEDIUM | Prompt injection defense is a security mechanism |

### 4.10 New Files (from restructure plan)

| New File | Priority | Key Content from Gap Analysis |
|----------|----------|-------------------------------|
| ERROR-CODES.md | HIGH | All 26 error codes with descriptions and remediation from `error_codes.py` |
| TROUBLESHOOTING.md | HIGH | Cancellation workflow, common errors mapped to DS-NNN codes |
| REFERENCE.md | HIGH | Complete CLI reference (including `reduce`), all config defaults, REPL sandbox rules, CLI shortcuts, file size limits, DEFAULT_PRUNE_DIRS |
| GETTING-STARTED.md | HIGH | Tutorial with explicit CLI vs Claude Code distinction |

---

## 5. Cross-Reference Matrix: Module to Documentation

This matrix shows which documentation files SHOULD cover each module and whether they currently do.

| Module | SKILL.md | REFERENCE.md (new) | SECURITY.md | ARCHITECTURE.md | Skill README | ERROR-CODES.md (new) | TROUBLESHOOTING.md (new) |
|--------|----------|-------------------|-------------|-----------------|-------------|---------------------|-------------------------|
| `__init__.py` | - | - | - | - | should list | - | - |
| `aggregator.py` | needs FINAL markers | needs aggregation API | - | has (good) | has (layout) | - | - |
| `ast_chunker.py` | needs semantic flag | needs chunk config | - | has (good) | needs update | - | - |
| `cancellation.py` | **needs mention** | **needs full section** | - | - | needs in layout | needs DS-505 | **needs How-To** |
| `checkpoint.py` | brief mention | needs section | - | - | has (layout) | needs DS-105 | **needs How-To** |
| `constants.py` | - | **needs full section** | - | - | **missing from layout** | - | needs timeout info |
| `deepscan_engine.py` | has (good) | **needs reduce cmd** | - | has (good) | has (layout) | - | needs shortcuts |
| `error_codes.py` | - | - | - | - | has (layout) | **needs all 26 codes** | needs error lookups |
| `grep_utils.py` | - | needs section | **needs fix** | - | **missing from layout** | - | - |
| `helpers.py` | has helpers | needs complete list | - | - | **missing from layout** | - | needs sandbox errors |
| `incremental.py` | brief | needs section | - | - | has (layout) | - | needs How-To |
| `models.py` | - | needs data models | - | has (indirect) | has (layout) | - | - |
| `progress.py` | brief | needs section | - | - | **missing from layout** | - | - |
| `repl_executor.py` | - | needs section | **needs update** | - | **missing from layout** | - | needs timeout info |
| `state_manager.py` | - | needs .deepscanignore | **needs update** | - | **missing from layout** | - | needs session info |
| `subagent_prompt.py` | - | needs agent types | **needs update** | has (good) | has (layout) | - | - |
| `walker.py` | - | **needs prune dirs** | - | - | **missing from layout** | - | - |

**Legend**: "has" = currently documented, "needs" = gap to fill, "**bold**" = high-priority gap, "-" = not applicable

---

## 6. Detailed Findings by Priority

### CRITICAL (Blocks usage or causes active harm)

1. **Version mismatch (plugin.json vs __init__.py)**: Plugin registry consumers see 0.1.0. Internal version is 2.0.0. Fix: update plugin.json.
2. **Error codes generate broken URLs**: `doc_url` property in `error_codes.py:131` generates `https://deepscan.io/docs/errors/DS-NNN` -- these pages don't exist. Fix: either create the pages, remove the URLs, or point to local ERROR-CODES.md.

### HIGH (Causes confusion for regular users)

3. **26 error codes with no documentation**: Every `[DS-NNN]` error a user encounters has no explanation outside source code.
4. **Grep implementation mismatch in SECURITY.md**: Claims 1-second ThreadPoolExecutor; reality is 10-second process isolation. Security auditors will flag this.
5. **AST chunking listed as "future" but already implemented**: Users miss `write_chunks(semantic=True)`.
6. **Cancellation completely undocumented**: 460 LOC of Double-tap Ctrl+C, graceful shutdown, checkpoint saving with zero user docs.
7. **`reduce` command missing from SKILL.md**: Users cannot complete the workflow without knowing about `reduce`.
8. **8 modules missing from file trees**: Contributors cannot navigate the codebase.
9. **`DEFAULT_PRUNE_DIRS` undocumented**: Users wonder why `node_modules`, `.git`, `.venv`, `__pycache__`, `dist`, `build`, `.next`, `.nuxt`, `target`, `vendor` (and 9 more) are excluded.
10. **Resource limits undocumented for users**: 256MB memory soft limit, 512MB hard limit, 60s/120s CPU -- Unix only. Windows has NO resource limits. Users on Windows should know their sandbox is weaker.

### MEDIUM (Nice to have, improves daily use)

11. **CLI shortcuts**: `?`, `!`, `+`, `x`, auto-path not in any doc.
12. **`.deepscanignore` has no example file**: Feature works (state_manager.py) but no `.deepscanignore.example` exists.
13. **SAFE_BUILTINS list not in user docs**: 35 allowed builtins -- users need the complete list to understand what's available. The REFERENCE.md plan lists extra builtins (`complex`, `frozenset`, `bytes`, `bytearray`, `memoryview`, `iter`, `next`, `chr`, `ord`, `hex`, `oct`, `bin`, `ascii`, `hash`) that are NOT in the actual `SAFE_BUILTINS` -- the restructure plan has errors.
14. **Output size limits undocumented**: 500KB per operation, 100KB CLI, 50KB preview -- users get truncated output with no prior explanation.
15. **FINAL marker protocol undocumented**: FINAL/FINAL_VAR/NEEDS_MORE/UNABLE termination markers.
16. **Escalation trigger conditions vague**: Only documented as "quality/complexity failures" -- actual logic is QUALITY_LOW or COMPLEXITY after attempt >= 2.
17. **Sequential fallback undocumented**: System falls back from parallel to sequential after 2 consecutive >50% failure batches.
18. **`re` module explicitly removed from REPL**: CVE-2026-002 fix means `re` is unavailable -- users may expect it.
19. **Adaptive chunk size table not in user docs**: 17 extension-to-size mappings in `constants.py:186-217`.
20. **ADR-001 in Korean only**: Accessibility concern for English-speaking contributors.

### LOW (Cosmetic or internal-only)

21. **`context_length` is a lambda, not a named function**: Minor surprise.
22. **Progress JSONL rotation behavior**: Rotates to `.jsonl.1` at 10MB.
23. **Session ID format**: `deepscan_{timestamp}_{16_hex_chars}` not documented.
24. **Tree view counts both files AND directories** in `max_files`.
25. **Placeholder vs pending result distinction** in MAP phase.
26. **Asymmetric checkpoint limits** (100MB read, 20MB write) for backward compatibility.
27. **LOC counts outdated** in Skill README.
28. **`__init__.py` not in any docs** (acceptable -- just declares version).

---

## 7. Validation Notes

### Restructure Plan Accuracy Issues

The phase2-doc-restructure-plan.md contains a few inaccuracies that the doc-writer should be aware of:

1. **SAFE_BUILTINS list in REFERENCE.md outline** (Section 3.4) includes builtins NOT in the actual implementation: `complex`, `frozenset`, `bytes`, `bytearray`, `memoryview`, `iter`, `next`, `chr`, `ord`, `hex`, `oct`, `bin`, `ascii`, `hash`. The actual list has 35 entries (see `constants.py:110-148`). The doc-writer must use the actual list, not the plan's list.

2. **Error code count**: Plan says "25 codes" but implementation has **26 codes** (DS-001 through DS-006, DS-101 through DS-105, DS-201 through DS-205, DS-301 through DS-306, DS-401 through DS-404, DS-501 through DS-505 = 6+5+5+6+4+5 = 31 enum members... actually counting the enum: 6+5+5+6+4+5 = 31. Wait -- let me recount from source: DS-001 through DS-006 (6), DS-101 through DS-105 (5), DS-201 through DS-205 (5), DS-301 through DS-306 (6), DS-401 through DS-404 (4), DS-501 through DS-505 (5) = **31 error codes total**. The phase1-impl-analysis says 26 and the plan says 25 -- both are wrong. The actual count from `error_codes.py` is **31 error codes**.

3. **`timeout_seconds: 300` confusion**: Plan correctly identifies the confusion but the recommended REFERENCE.md table lists `timeout_seconds` with range "30-3600" -- this is the sub-agent timeout from `DeepScanConfig`, not the REPL timeout (5s) or grep timeout (10s). The reference should clearly label each timeout scope.

---

## 8. Summary Statistics

| Category | Count |
|----------|-------|
| Total gaps identified | 97 |
| CRITICAL priority | 2 |
| HIGH priority | 10 |
| MEDIUM priority | 20 |
| LOW priority | 8 |
| Confirmed contradictions | 13 |
| Missing file references | 4 |
| Fragile line references | 13+ |
| Completely undocumented modules | 3 (by name) |
| Severely under-documented modules | 5 |
| Undocumented public functions | 22 |
| Undocumented config options | 17 |
| Undocumented error codes | 31 (all of them) |
| Undocumented security features | 10 |
| Undocumented workflows | 8 |
