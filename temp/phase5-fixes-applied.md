# Phase 5: V1 Fixes Applied

> **Agent**: doc-fixer
> **Date**: 2026-02-16
> **Task**: #12 -- Apply all fixes from Verification Round 1

---

## Summary

Applied **17 fixes** across **8 documentation files**. All fixes were verified against source code before applying.

---

## Fixes Applied

### CRITICAL (0 needed -- already fixed)

| # | File | Fix | Source Verified |
|---|------|-----|-----------------|
| 1 | CLAUDE.md:13 | Version already shows `v2.0.0` (fixed in previous phase) | `plugin.json:3` = `"2.0.0"` |

### HIGH PRIORITY -- V1 Accuracy Fixes (6 fixes)

| # | File | Fix | Source Verified |
|---|------|-----|-----------------|
| 2 | GETTING-STARTED.md:102 | Changed file header delimiter `---` to `===` | `state_manager.py:161` uses `=== FILE: {rel_path} ===` |
| 3 | TROUBLESHOOTING.md:146 | Changed graceful timeout from `10-second` to `30-second` | `deepscan_engine.py:1289` passes `graceful_timeout=30.0` |
| 4 | SECURITY.md:281 | Changed ReDoS patterns from `12` to `13` (two locations: prose and code comment) | `constants.py:156-176` has 13 patterns |
| 5 | REFERENCE.md Resource Limits | Changed File size soft limit from `--` to `10MB` | `repl_executor.py:91` sets both soft and hard to 10MB |
| 6 | REFERENCE.md Timeouts | Changed Graceful cancellation from `10s` to `30s` | `deepscan_engine.py:1289` uses 30.0 |
| 7 | ARCHITECTURE.md:337 | Changed `init_parser (line 1431)` to descriptive reference `(search for --agent-type in init_parser)` | `deepscan_engine.py:1657-1663` is actual location |

### HIGH PRIORITY -- V1 Usability Fixes (3 fixes)

| # | File | Fix | Source Verified |
|---|------|-----|-----------------|
| 8 | GETTING-STARTED.md | Added **Poetry** to Prerequisites with pip alternative | N/A (usability) |
| 9 | README.md (root) | Added **Poetry** to Prerequisites with pip alternative | N/A (usability) |
| 10 | GETTING-STARTED.md | Added "How to run commands" callout before Step 3, explaining CLI prefix vs Claude Code direct invocation | N/A (usability) |

### HIGH PRIORITY -- Configuration Documentation (1 fix)

| # | File | Fix | Source Verified |
|---|------|-----|-----------------|
| 11 | REFERENCE.md | Added "Configuration File" explanation section before settings table, explaining that config is set via CLI flags and function parameters (no external config file) | `models.py:157-177` DeepScanConfig Pydantic model |

### MUST FIX -- UX Review (2 fixes)

| # | File | Fix | Source Verified |
|---|------|-----|-----------------|
| 12 | USE_CASES.md:295 | Rewrote `__setitem__` REPL example to use standard dict assignment in a for loop (sandbox-safe) | `deepscan_engine.py:451-462` blocks `_`-prefixed attributes |
| 13 | SECURITY.md:311 | Added clarifying note to unchecked checklist item explaining it is a known testing gap with reference to TEST-PLAN.md | N/A (documentation clarity) |

### SHOULD FIX -- Skill README Cleanup (3 fixes)

| # | File | Fix | Source Verified |
|---|------|-----|-----------------|
| 14 | Skill README.md:85 | Removed `(D2-FIX)` internal annotation from heading | N/A (cleanup) |
| 15 | Skill README.md:155 | Removed `(P5.2)` internal annotation from heading | N/A (cleanup) |
| 16 | Skill README.md:433 | Changed `(Phase 8)` to `(Phase 7)` in Timeout Behavior heading | Plugin is at Phase 7 (v2.0.0) |

### MEDIUM -- Line Range Precision (1 fix)

| # | File | Fix | Source Verified |
|---|------|-----|-----------------|
| 17 | SECURITY.md:9 | Widened attribute blocking line range from `453-459` to `451-462` (includes enforcement logic) | `deepscan_engine.py:451-462` |

---

## Verified Correct (No Fix Needed)

| Claim | Verified Value | Source |
|-------|---------------|--------|
| CLAUDE.md version | v2.0.0 | `plugin.json:3` |
| SAFE_BUILTINS count | 36 entries | `constants.py:110-148` (counted each key-value pair) |
| FORBIDDEN_PATTERNS count | 15 patterns | Already correct in docs |
| DANGEROUS_ATTRS count | 19 attributes | Already correct in docs |
| Phase 8 in Skill README roadmap | Correct -- refers to future work | Not a bug |

---

## Files Modified

1. `/home/idnotbe/projects/deepscan/.claude/skills/deepscan/docs/GETTING-STARTED.md` (3 edits)
2. `/home/idnotbe/projects/deepscan/.claude/skills/deepscan/docs/TROUBLESHOOTING.md` (1 edit)
3. `/home/idnotbe/projects/deepscan/.claude/skills/deepscan/docs/SECURITY.md` (4 edits)
4. `/home/idnotbe/projects/deepscan/.claude/skills/deepscan/docs/REFERENCE.md` (3 edits)
5. `/home/idnotbe/projects/deepscan/.claude/skills/deepscan/docs/ARCHITECTURE.md` (1 edit)
6. `/home/idnotbe/projects/deepscan/.claude/skills/deepscan/docs/USE_CASES.md` (1 edit)
7. `/home/idnotbe/projects/deepscan/.claude/skills/deepscan/README.md` (3 edits)
8. `/home/idnotbe/projects/deepscan/README.md` (1 edit)

---

## Not Applied (Out of Scope or Deferred)

| Item | Reason |
|------|--------|
| FINAL marker protocol documentation | Gap R1 from completeness report -- new content, not a fix |
| Unicode lookalike enumeration | Gap R2 -- new content, not a fix |
| Ghost findings documentation | Gap R3 -- new content, not a fix |
| Skill README length/audience split | SHOULD FIX from UX but requires structural rewrite, not a simple fix |
| Reset command description | SHOULD FIX from UX -- requires source verification of exact behavior |
| DS-505 remediation prominence | SHOULD FIX from UX -- cosmetic improvement |
| NICE TO HAVE items (14 total) | Deferred per priority |
