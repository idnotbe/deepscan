# Phase 4 - Verification Round 1: Technical Accuracy Report

> **Agent**: v1-accuracy
> **Task**: #9 — Independently verify every technical claim in documentation against actual Python source code
> **Date**: 2026-02-16
> **Status**: COMPLETE

---

## Executive Summary

Reviewed **11 documentation files** against **17 Python source modules** plus `plugin.json`. Found **14 inaccuracies**: 1 CRITICAL, 5 HIGH, 5 MEDIUM, 3 LOW. Most issues are numeric mismatches (counts, timeouts, line numbers) or formatting discrepancies between documentation claims and actual implementation.

---

## Methodology

1. Read all 17 Python source files to establish a ground truth baseline
2. Read all 11 documentation files systematically
3. Cross-referenced every verifiable claim (counts, constants, line numbers, function signatures, format strings, version numbers) against source code
4. Rated each inaccuracy by severity

### Severity Definitions

| Rating | Meaning |
|--------|---------|
| **CRITICAL** | Misleading or dangerous — could cause user errors or security misunderstanding |
| **HIGH** | Factually wrong information — user will encounter contradictions |
| **MEDIUM** | Imprecise or outdated — could confuse but unlikely to cause harm |
| **LOW** | Cosmetic — minor inconsistency unlikely to affect usage |

---

## Findings

### Finding 1: CLAUDE.md — Wrong plugin.json version

- **Severity**: CRITICAL
- **Doc**: `CLAUDE.md:9` — States `.claude-plugin/plugin.json | Plugin manifest (v0.1.0)`
- **Code**: `.claude-plugin/plugin.json:3` — `"version": "2.0.0"`
- **Also**: `scripts/models.py` DeepScanState default version is `"2.0.0"`, Skill README says `Version: 2.0.0 (Phase 7)`
- **Impact**: CLAUDE.md is the primary instruction file for Claude Code agents. An agent reading this will believe the plugin is at v0.1.0 when it's actually v2.0.0. This undermines trust in the instruction file.
- **Fix**: Change `v0.1.0` to `v2.0.0` in CLAUDE.md line 9.

---

### Finding 2: GETTING-STARTED.md — Wrong file header delimiter format

- **Severity**: HIGH
- **Doc**: `GETTING-STARTED.md:102` — States headers look like `--- FILE: src/app.py ---`
- **Code**: `state_manager.py:161` — Actual format is `f"=== FILE: {rel_path} ===\n"` (uses `===` not `---`)
- **Impact**: A user following the tutorial will see `===` delimiters in actual output but the docs show `---`. This creates confusion during first use.
- **Fix**: Change `--- FILE: src/app.py ---` to `=== FILE: src/app.py ===` in GETTING-STARTED.md.

---

### Finding 3: TROUBLESHOOTING.md — Wrong graceful cancellation timeout

- **Severity**: HIGH
- **Doc**: `TROUBLESHOOTING.md:146` — States "The graceful shutdown has a 10-second timeout"
- **Code**: `deepscan_engine.py:1289` — `cmd_map` passes `graceful_timeout=30.0`
- **Also**: `cancellation.py` default parameter is `graceful_timeout: float = 10.0`, but the actual caller (`cmd_map`) overrides to 30.0
- **Impact**: User expects 10 seconds but will wait 30 seconds during cancellation. User may force-quit prematurely thinking something is stuck.
- **Fix**: Change "10-second timeout" to "30-second timeout" in TROUBLESHOOTING.md, or clarify that default is 10s but map uses 30s.

---

### Finding 4: SECURITY.md — Wrong ReDoS pattern count

- **Severity**: HIGH
- **Doc**: `SECURITY.md:281` — States "12 known ReDoS patterns checked before execution"
- **Code**: `constants.py:156-176` — `REDOS_PATTERNS` contains **13** patterns
- **Actual patterns** (counted from constants.py):
  1. `(a+)+`
  2. `(a*)+`
  3. `(a+)*`
  4. `(a*)*`
  5. `(?:a+)+`
  6. `(?:a*)+`
  7. `(?P<name>a+)+`
  8. `(?P<name>a*)+`
  9. `(a|a)+`
  10. `(a|a)*`
  11. `([a-z]+)+`
  12. `(.*){n}`
  13. `(pattern){n,}`
- **Impact**: Security documentation undercounts a defense mechanism. Minor but undermines precision of security claims.
- **Fix**: Change "12 known ReDoS patterns" to "13 known ReDoS patterns" in SECURITY.md.

---

### Finding 5: REFERENCE.md — Wrong resource limits table (file size soft limit)

- **Severity**: HIGH
- **Doc**: `REFERENCE.md` Resource Limits table — Shows `--` (dash) for File size soft limit, implying no soft limit
- **Code**: `repl_executor.py:91` — `resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024, 10 * 1024 * 1024))` — Both soft AND hard limits are 10MB
- **Impact**: Documentation implies there's no soft file size limit, but the code sets both soft and hard to 10MB.
- **Fix**: Change the soft limit cell from `--` to `10MB` in the Resource Limits table.

---

### Finding 6: ARCHITECTURE.md — Wrong line number reference for init_parser

- **Severity**: HIGH
- **Doc**: `ARCHITECTURE.md:337` — States "Update CLI choices in `deepscan_engine.py` init_parser (line 1431)"
- **Code**: `deepscan_engine.py` — The `init_parser` with `--agent-type` choices is around lines 1657-1663 (not 1431)
- **Impact**: A contributor following the extension guide will look at the wrong line and waste time. Could lead to incorrect modifications.
- **Fix**: Update line reference to approximately 1660 (or remove specific line numbers in favor of function/variable names).

---

### Finding 7: USE_CASES.md — Example uses sandbox-blocked dunder method

- **Severity**: MEDIUM
- **Doc**: `USE_CASES.md:295` — Example: `[exts.__setitem__(f.rsplit('.',1)[-1], exts.get(f.rsplit('.',1)[-1],0)+1) for f in get_status()['files']]`
- **Code**: `deepscan_engine.py:451-462` — Layer 3 blocks ALL underscore-prefixed attributes: `if node.attr.startswith("_"): raise SecurityError`
- **Impact**: User copying this example into the REPL will get a security error. Documentation provides a non-functional example.
- **Fix**: Rewrite the example to avoid dunder access. For example, use a regular dict update pattern or `collections.Counter`.

---

### Finding 8: REFERENCE.md — Graceful cancellation timeout inconsistency

- **Severity**: MEDIUM
- **Doc**: `REFERENCE.md` Cancellation section — States "Graceful cancellation | 10s"
- **Code**: `deepscan_engine.py:1289` — `cmd_map` uses `graceful_timeout=30.0`
- **Impact**: Same issue as Finding 3 but in a different document. The 10s value is the function default but not the actual runtime value for the `map` command.
- **Fix**: Clarify that map uses 30s timeout, or state the range (10-30s depending on command).

---

### Finding 9: Skill README.md — "Phase 8" heading should be "Phase 7"

- **Severity**: MEDIUM
- **Doc**: Skill `README.md` around line 433 — Heading says "**Timeout Behavior (Phase 8)**:"
- **Code**: The plugin is at Phase 7 (v2.0.0), as stated elsewhere in the same README
- **Impact**: Implies features from a future phase are present. Confusing for users and contributors tracking development.
- **Fix**: Change "Phase 8" to "Phase 7".

---

### Finding 10: Skill README.md — Internal annotations visible to users

- **Severity**: MEDIUM
- **Doc**: Skill `README.md` — Contains `D2-FIX` and `P5.2` annotations
- **Impact**: Internal development markers are exposed to end users. Appears unpolished and confusing.
- **Fix**: Remove all internal annotations from user-facing documentation.

---

### Finding 11: SECURITY.md — "Security at a Glance" table line number ranges

- **Severity**: MEDIUM
- **Doc**: `SECURITY.md:9` — States "Attribute blocking | 19 dangerous dunder attributes blocked | `deepscan_engine.py:453-459`"
- **Code**: `deepscan_engine.py` — `DANGEROUS_ATTRS` frozenset is at lines 453-459, but the actual enforcement check (`if node.attr.startswith("_")`) extends to line 462
- **Impact**: Minor — the referenced lines show the constant but not the enforcement logic. A contributor might miss the enforcement code.
- **Fix**: Widen the range to `deepscan_engine.py:451-462` or clarify what the range covers.

---

### Finding 12: CLAUDE.md — Slightly imprecise line ranges for security code

- **Severity**: LOW
- **Doc**: `CLAUDE.md` — States "Forbidden pattern regex (lines 344-367)"
- **Code**: `deepscan_engine.py` — FORBIDDEN_PATTERNS starts at line 345 (not 344), the patterns end at line 361, and the validation loop continues to ~366
- **Impact**: Very minor. The range is close but not exact. A contributor will find the code quickly regardless.
- **Fix**: Adjust to "lines 345-366" for precision, or leave as-is since it's close enough.

---

### Finding 13: ARCHITECTURE.md — LOC estimates potentially outdated

- **Severity**: LOW
- **Doc**: `ARCHITECTURE.md:278-293` — Lists LOC for each module (e.g., "deepscan_engine.py (~2500 LOC)")
- **Code**: Source files may have grown or shrunk since estimates were written
- **Impact**: LOC counts are approximate and may drift. Not harmful but could be misleading.
- **Fix**: Either remove LOC estimates or add "(approximate)" qualifier.

---

### Finding 14: SECURITY.md — Unchecked security checklist item

- **Severity**: LOW
- **Doc**: `SECURITY.md:311` — `[ ] Test for path traversal with .. and symlinks` is unchecked
- **Code**: `walker.py` uses `follow_symlinks=False` and `ast_chunker.py` uses `resolve(strict=True) + relative_to()` — protections exist but are untested
- **Impact**: The checklist honestly reflects the state (no tests exist). This is documented in CLAUDE.md as a known gap. Not an inaccuracy per se, but flagged since it's a security item visible to users.
- **Fix**: Either implement the tests, or move the checklist to an internal tracking document.

---

## Verified Claims (Confirmed Accurate)

The following major claims were verified as **correct**:

| Claim | Document | Verified Against |
|-------|----------|-----------------|
| SAFE_BUILTINS has 36 entries | REFERENCE.md, SECURITY.md | `constants.py:110-148` — counted 36 |
| 15 forbidden patterns | REFERENCE.md, SECURITY.md | `deepscan_engine.py:345-361` — counted 15 |
| 19 dangerous dunder attributes | REFERENCE.md, SECURITY.md | `deepscan_engine.py:453-459` — counted 19 |
| 31 error codes (DS-NNN) | ERROR-CODES.md, ARCHITECTURE.md | `error_codes.py` — 6+5+5+6+4+5=31 |
| All error code names, messages, exit codes | ERROR-CODES.md | `error_codes.py` ErrorCode enum — all match |
| Memory limits 256MB/512MB | SECURITY.md, REFERENCE.md | `repl_executor.py:82-87` — correct |
| CPU limits 60s/120s | SECURITY.md, REFERENCE.md | `repl_executor.py:88-90` — correct |
| DEFAULT_PRUNE_DIRS has 19 directories | TROUBLESHOOTING.md | `walker.py` DEFAULT_PRUNE_DIRS — counted 19 |
| Chunk size range 50K-300K | REFERENCE.md | `helpers.py` chunk_indices validation — correct |
| Overlap range 0-50K | ERROR-CODES.md (DS-005) | `helpers.py` — `0 <= overlap <= 50_000` — correct |
| SUPPORTED_AGENT_TYPES list | ARCHITECTURE.md, SKILL.md | `subagent_prompt.py` — ["general", "security", "architecture", "performance"] — correct |
| XML boundary structure for prompt injection | SECURITY.md | `subagent_prompt.py` — uses SYSTEM_INSTRUCTIONS, DATA_CONTEXT, USER_QUERY tags — correct |
| Session hash format | ARCHITECTURE.md | `state_manager.py` — `secrets.token_hex(8)` — correct |
| Pydantic + JSON serialization (no pickle) | SECURITY.md, ARCHITECTURE.md | All state files use `model_dump_json()` — correct |
| Write isolation to ~/.claude/cache/deepscan/ | SECURITY.md | `state_manager.py:381-398` _safe_write — correct |
| Max parallel agents = 5 | ARCHITECTURE.md | `models.py` DeepScanConfig default — correct |
| Default chunk size = 150,000 | REFERENCE.md | `constants.py` DEFAULT_CHUNK_SIZE — correct |
| follow_symlinks=False in walker | SECURITY.md | `walker.py` — confirmed at multiple call sites |
| Project-root enforcement in ast_chunker | SECURITY.md, CLAUDE.md | `ast_chunker.py:400-419` — confirmed |

---

## Summary Statistics

| Severity | Count |
|----------|-------|
| CRITICAL | 1 |
| HIGH | 5 |
| MEDIUM | 5 |
| LOW | 3 |
| **Total** | **14** |

### Priority Fixes

1. **CLAUDE.md version** (Finding 1) — Fix immediately, agents rely on this
2. **File header delimiter** (Finding 2) — Fix for first-run experience
3. **Graceful timeout values** (Findings 3, 8) — Fix in both TROUBLESHOOTING.md and REFERENCE.md
4. **ReDoS pattern count** (Finding 4) — Fix for security documentation precision
5. **Resource limits table** (Finding 5) — Fix for accuracy
6. **init_parser line reference** (Finding 6) — Fix for contributor guidance
7. **Sandbox-blocked example** (Finding 7) — Fix for usability

---

## Cross-Reference with UX Review (Phase 3)

The UX reviewer (phase3-ux-feedback.md) independently flagged two items that overlap with this report:

| UX Finding | This Report |
|------------|-------------|
| USE_CASES.md `__setitem__` example blocked by sandbox | Finding 7 (MEDIUM) |
| SECURITY.md unchecked checklist item | Finding 14 (LOW) |

Both are confirmed as real issues through independent verification.
