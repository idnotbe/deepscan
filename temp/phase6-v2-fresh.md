# Phase 6 V2 Fresh Perspective Review

**Reviewer**: v2-fresh (no prior context)
**Date**: 2026-02-16
**Scope**: All 11 documentation files for the DeepScan Claude Code plugin

---

## 1. First Impressions

Walking into this documentation cold, my first impression is notably positive. The documentation set is comprehensive and well-organized for a plugin at this stage. There is a clear separation of concerns: a top-level README for orientation, a CLAUDE.md for developer policy, a SKILL.md for the Claude Code interface, a detailed inner README for contributors, and a full suite of reference docs (getting-started, reference, error-codes, troubleshooting, architecture, security, use-cases). The writing is direct and technical without being impenetrable. The biggest surprise was discovering this is a security-sensitive tool with zero tests -- but the documentation is transparent about this gap, which is commendable.

---

## 2. Navigation Assessment

### Doc Map (how docs relate to each other)

| Role | File | Audience |
|------|------|----------|
| Entry point / overview | `README.md` (root) | All users |
| Developer policy | `CLAUDE.md` | AI agents, contributors |
| Skill interface | `.claude/skills/deepscan/SKILL.md` | Claude Code runtime |
| Contributor guide | `.claude/skills/deepscan/README.md` | Developers |
| Tutorial | `docs/GETTING-STARTED.md` | First-time users |
| Lookup reference | `docs/REFERENCE.md` | Experienced users |
| Error catalog | `docs/ERROR-CODES.md` | All users (troubleshooting) |
| How-to guide | `docs/TROUBLESHOOTING.md` | Users with problems |
| Internals | `docs/ARCHITECTURE.md` | Contributors |
| Security model | `docs/SECURITY.md` | Security reviewers, contributors |
| Scenarios | `docs/USE_CASES.md` | All users |

### Navigation Strengths

- Cross-references are consistent: almost every doc ends with a "See Also" or "References" section linking to related docs.
- The root README has a clear documentation table with all docs listed.
- GETTING-STARTED.md ends with "What's Next" links -- good progressive disclosure.
- TROUBLESHOOTING.md links to specific ERROR-CODES.md anchors (e.g., `#ds-306-session-not-found`).

### Navigation Weaknesses

- **Two READMEs**: There is a root `README.md` and a `.claude/skills/deepscan/README.md`. The root is user-facing; the inner one is developer-facing. This is not immediately obvious. A new contributor might land on the inner README first via GitHub directory browsing and be confused by the overlap.
- **CLAUDE.md vs inner README overlap**: Both describe security-critical modules, testing gaps, and repository layout. Keeping them in sync is a maintenance burden.
- **ADR-001 is in Korean**: The ADR (`ADR-001-repl-security-relaxation.md`) is entirely in Korean. This is fine if the team is Korean-speaking, but it is a jarring break from the English-only rest of the documentation. No English docs mention this language mismatch.

---

## 3. Accuracy Spot-Check Results (10 Claims Verified)

### Claim 1: "17 modules" in scripts/
**Source**: CLAUDE.md line 9, inner README line 334-350
**Verification**: `ls .claude/skills/deepscan/scripts/*.py | wc -l` = **17**
**Result**: PASS

### Claim 2: "SAFE_BUILTINS" has 36 entries
**Source**: REFERENCE.md line 225, SECURITY.md line 12
**Verification**: Counted entries in `constants.py:110-148` = **36**
**Result**: PASS

### Claim 3: "31 DS-NNN error codes"
**Source**: SKILL.md line 212, CLAUDE.md line 70, ERROR-CODES.md
**Verification**: Counted enum members in `error_codes.py:60-101` = 6+5+5+6+4+5 = **31**
**Result**: PASS

### Claim 4: "15 forbidden regex patterns" in Layer 1
**Source**: SECURITY.md line 9, REFERENCE.md line 263
**Verification**: Counted patterns in `deepscan_engine.py:345-361` = **15**
**Result**: PASS

### Claim 5: "19 dangerous dunder attributes" blocked
**Source**: SECURITY.md line 11, REFERENCE.md line 275
**Verification**: Counted entries in `deepscan_engine.py:453-459` = **19**
**Result**: PASS

### Claim 6: Plugin version is "v0.1.0" (CLAUDE.md) vs "2.0.0" (plugin.json)
**Source**: CLAUDE.md line 13 says "v0.1.0"; plugin.json says "2.0.0"; inner README line 3 says "2.0.0"; `models.py:198` says `version: str = "2.0.0"`
**Verification**: `plugin.json` has `"version": "2.0.0"`. Source code default is `"2.0.0"`.
**Result**: FAIL -- CLAUDE.md line 13 says `v0.1.0` but should say `v2.0.0`. This is a version mismatch.

### Claim 7: "follow_symlinks=False" in walker.py
**Source**: CLAUDE.md line 37, SECURITY.md line 275
**Verification**: `walker.py:207,216,220` all use `follow_symlinks=False`
**Result**: PASS

### Claim 8: Resource limits are "256MB/512MB memory, 60s/120s CPU"
**Source**: SECURITY.md line 13, REFERENCE.md lines 336-339
**Verification**: `repl_executor.py:87` = `(256*1024*1024, 512*1024*1024)`, line 89 = `(60, 120)`, line 91 = `(10*1024*1024, 10*1024*1024)`
**Result**: PASS

### Claim 9: "4 agent types: general, security, architecture, performance"
**Source**: SKILL.md lines 154-161, REFERENCE.md lines 214-219
**Verification**: `subagent_prompt.py:43` = `["general", "security", "architecture", "performance"]`
**Result**: PASS

### Claim 10: "19 directories auto-excluded" during traversal
**Source**: REFERENCE.md lines 376-378, TROUBLESHOOTING.md line 232
**Verification**: `walker.py:403-424` `DEFAULT_PRUNE_DIRS` has exactly **19** entries
**Result**: PASS

### Summary: 9/10 claims verified. 1 version mismatch in CLAUDE.md.

---

## 4. Strengths (What's Done Well)

1. **Honest about gaps**: The "No tests exist yet" callout appears in README.md, CLAUDE.md, and the inner README. This is unusually transparent for project documentation and helps contributors understand the risk profile.

2. **Security documentation is excellent**: SECURITY.md is one of the best security docs I have seen for a project this size. It has a clear threat model, labeled attack vectors with risk levels, ASCII diagrams of the defense layers, and actionable code examples showing why certain things are blocked. The "Why getattr is dangerous" snippet is particularly well done.

3. **Error code system is thorough**: 31 error codes with consistent format, categorization, exit codes, causes, and fixes. The ERROR-CODES.md is a proper reference document -- it reads like a well-structured man page.

4. **Progressive disclosure works**: A new user can follow README -> GETTING-STARTED -> TROUBLESHOOTING without hitting any dead ends. Each step leads naturally to the next.

5. **Consistent cross-references**: Nearly every document links to related docs. The "See Also" sections are useful and accurate.

6. **Practical examples**: GETTING-STARTED.md shows expected output for each command, which helps users know if things are working correctly. USE_CASES.md provides realistic scenarios with actual commands.

7. **CLI vs Claude Code distinction**: The docs consistently explain the dual-environment behavior, with the table in GETTING-STARTED.md and REFERENCE.md being especially clear.

8. **REFERENCE.md is comprehensive**: It covers commands, config, REPL sandbox, size limits, timeouts, adaptive chunk sizes, file locations, and session ID format. This is a strong single-source-of-truth for technical details.

---

## 5. Issues Found

### Issue 1: Version mismatch in CLAUDE.md
**File**: `/home/idnotbe/projects/deepscan/CLAUDE.md:13`
**Severity**: Low
**Details**: CLAUDE.md says `Plugin manifest (v0.1.0)` but `plugin.json` says `"version": "2.0.0"` and `models.py` defaults to `version: "2.0.0"`. All other docs reference v2.0.0 or "Phase 7".

### Issue 2: CLAUDE.md references "8 documentation files" but there are now more
**File**: `/home/idnotbe/projects/deepscan/CLAUDE.md:10`
**Severity**: Low
**Details**: Line 10 says "8 documentation files" in the docs directory. Actual count in the `docs/` folder is 8 (GETTING-STARTED, REFERENCE, ERROR-CODES, TROUBLESHOOTING, ARCHITECTURE, SECURITY, USE_CASES, ADR-001). This is technically correct if counting only `docs/` files. The total documentation set across the project is 11 files. Borderline issue -- the scope is ambiguous.

### Issue 3: ADR-001 is entirely in Korean
**File**: `/home/idnotbe/projects/deepscan/.claude/skills/deepscan/docs/ADR-001-repl-security-relaxation.md`
**Severity**: Medium
**Details**: Every other document is in English. The ADR is entirely in Korean. For an open-source plugin, this creates an accessibility gap. The ADR contains important security rationale (why certain AST nodes were allowed/blocked). Contributors who don't read Korean will miss this context.

### Issue 4: ADR-001 contains outdated information about resource limits
**File**: `/home/idnotbe/projects/deepscan/.claude/skills/deepscan/docs/ADR-001-repl-security-relaxation.md:126-144`
**Severity**: Medium
**Details**: Line 126 says memory limits are "currently not implemented, planned for Phase 8" and line 143 says hard memory limits via cgroups/rlimit are not implemented. But `repl_executor.py:82-94` clearly implements `resource.setrlimit` for memory, CPU, and file size. The ADR is out of date -- resource limits HAVE been implemented since the ADR was written.

### Issue 5: SECURITY.md Section 6.2 HMAC note could confuse readers
**File**: `/home/idnotbe/projects/deepscan/.claude/skills/deepscan/docs/SECURITY.md:227-244`
**Severity**: Low
**Details**: The HMAC section includes a full code example of how HMAC signing "would work" and clearly labels it as "PLANNED - not currently in any module". This is well-labeled but including implementation code for a non-existent feature in a security document could mislead security reviewers doing a quick scan. Consider moving to an ADR or future-work section.

### Issue 6: SECURITY.md line references may drift
**File**: `/home/idnotbe/projects/deepscan/.claude/skills/deepscan/docs/SECURITY.md:9-16`
**Severity**: Low
**Details**: The "Security at a Glance" table references specific line numbers (e.g., `deepscan_engine.py:345-361`, `constants.py:109-148`). These match current source code, but line references are fragile and will become inaccurate as the code evolves. The same issue exists in CLAUDE.md. This is a known maintenance challenge with no easy fix.

### Issue 7: Troubleshooting mentions "CVE-2026-002" without explanation
**File**: `/home/idnotbe/projects/deepscan/.claude/skills/deepscan/docs/TROUBLESHOOTING.md:34`
**Severity**: Low
**Details**: The troubleshooting table says `re` module was removed due "CVE-2026-002" but this CVE is not explained anywhere in the documentation. REFERENCE.md line 261 also mentions it. If this is an internal CVE-like identifier, it should be documented; if it is a real CVE, a link would be helpful.

### Issue 8: Inner README LOC counts may drift
**File**: `/home/idnotbe/projects/deepscan/.claude/skills/deepscan/README.md:334-481`
**Severity**: Low
**Details**: The inner README lists exact LOC counts for every module (e.g., `deepscan_engine.py: ~2500 LOC`). These are helpful for orientation but will become inaccurate as the code evolves. The `~` prefix helps but does not eliminate the drift problem.

---

## 6. Overall Quality Score

**Score: 8/10**

### Breakdown

| Dimension | Score | Notes |
|-----------|-------|-------|
| Accuracy | 9/10 | 9 of 10 spot checks passed; only version mismatch |
| Completeness | 8/10 | Covers all major topics; ADR language gap |
| Organization | 9/10 | Clear hierarchy, good cross-references |
| Navigation | 8/10 | Two READMEs can confuse; otherwise strong |
| Consistency | 7/10 | Version mismatch, ADR language mismatch, one outdated ADR |
| Examples | 9/10 | Practical, show expected output, correct syntax |
| Security docs | 10/10 | Exceptional -- threat model, defense layers, code examples |
| Maintenance burden | 6/10 | Line number references and LOC counts will drift |

### Why Not Higher

The 2-point gap comes from: (1) the ADR being in a different language from the rest of the docs, (2) the version inconsistency in CLAUDE.md, (3) the fragility of line-number references and LOC counts that will inevitably drift, and (4) mild overlap between CLAUDE.md and the inner README that creates a sync burden.

### Why Not Lower

The fundamentals are strong. A new user has a clear path from README to GETTING-STARTED to productive use. A security reviewer has a detailed threat model. A contributor has architecture docs and extension points. Error codes are comprehensive and well-referenced. The documentation is honest about its own gaps. This is above average for a project of this size and complexity.

---

## 7. Final Recommendations

### Must Fix (Before Release)

1. **Fix CLAUDE.md version**: Change `v0.1.0` to `v2.0.0` on line 13 to match `plugin.json` and all other docs.

### Should Fix (High Value)

2. **Translate or create English version of ADR-001**: The security rationale in this ADR is important for contributors. Either translate it or create an English summary alongside it.

3. **Update ADR-001 resource limit claims**: The ADR says resource limits are not implemented, but they are. Update Section 5 (DoS defense) to reflect the current state.

### Nice to Have

4. **Consider function/module references instead of line numbers**: Replace `deepscan_engine.py:345-361` with `deepscan_engine.py: FORBIDDEN_PATTERNS list in validate_and_execute()` for more stable references.

5. **Add a note about CVE-2026-002**: Either link to it or explain it is an internal identifier. Currently it appears in TROUBLESHOOTING.md and REFERENCE.md without context.

6. **Consider merging CLAUDE.md security sections with inner README**: The overlap between these two files creates a sync maintenance burden. CLAUDE.md could reference the inner README rather than duplicating the security module table.
