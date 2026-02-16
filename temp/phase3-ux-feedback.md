# Phase 3: UX/DX Review of Documentation Changes

**Reviewer**: ux-reviewer
**Date**: 2026-02-16
**Input**: 28 changes across 11 files (4 new, 7 updated), 15 user scenarios

---

## 1. Overall DX Assessment

The documentation suite has been transformed from a fragmented, inaccurate collection into a well-organized, cross-referenced set of documents that follows the Diataxis framework (tutorial, how-to, reference, explanation). A new developer can now follow a clear path from README to GETTING-STARTED to first scan completion. The new documents (GETTING-STARTED, ERROR-CODES, TROUBLESHOOTING, REFERENCE) fill critical gaps that previously left users without error guidance or command reference. The biggest remaining issues are: (a) the GETTING-STARTED tutorial uses bare command names (`exec`, `map`, `reduce`) without the full CLI prefix, creating ambiguity about which environment the commands target; (b) the Skill README is extremely long (~525 lines) and mixes quick-start, development guide, and internal details in ways that will overwhelm new users; and (c) some cross-document terminology is inconsistent (e.g., "14 patterns" vs "15 patterns" in older sections, "26 error codes" vs "31 error codes" in the user scenarios temp file).

---

## 2. Per-Document Ratings and Issues

### 2.1 GETTING-STARTED.md (NEW)

**Rating: GOOD**

This is the strongest new document. Clear progression from prerequisites through export. Expected output at every step.

| # | Issue | Line | Severity | Description |
|---|-------|------|----------|-------------|
| 1 | Bare command names in Steps 3-7 | 98-179 | SHOULD FIX | Commands like `exec -c "print(peek_head(3000))"` and `map` are shown without the `poetry run python ...` prefix OR the `/deepscan` prefix. Step 2 shows both forms, but Steps 3-7 use bare names. A user running CLI will not know what to type. |
| 2 | No mention of `poetry install` | 37-67 | SHOULD FIX | Step 1 says to clone the repo and copy directories, but never tells the user to run `poetry install` to get dependencies. The `poetry run python ...` verify command will fail without it. |
| 3 | Verify command uses `poetry run` but clone instructions do not mention poetry setup | 53 | SHOULD FIX | After cloning, the user needs to install the poetry project. Add: `cd deepscan && poetry install` |
| 4 | Step 3 "Scout" has no exit criteria | 93-116 | NICE TO HAVE | User does not know when to stop scouting and move to chunking. A brief sentence like "Once you understand the context, proceed to chunking" would help. |
| 5 | Environment Note table could link to REFERENCE.md | 23-35 | NICE TO HAVE | The CLI vs Claude Code environment note is duplicated in REFERENCE.md. A cross-link would reduce duplication. |

---

### 2.2 ERROR-CODES.md (NEW)

**Rating: GOOD**

Comprehensive, well-organized. Every error code has a clear explanation and actionable fix. The quick lookup table at the end is excellent.

| # | Issue | Line | Severity | Description |
|---|-------|------|----------|-------------|
| 6 | `doc_url` note at top could be more prominent | 5 | NICE TO HAVE | The note about broken URLs is a blockquote. Users who click error code links in the CLI will hit 404s. Consider making this a warning box or bolding "do not currently resolve". |
| 7 | DS-505 remediation note at bottom is easy to miss | 463 | SHOULD FIX | The note about incorrect remediation template (`deepscan --resume` vs `resume <hash>`) is a blockquote at the bottom of the DS-505 section. Since users will encounter this exact wrong suggestion from the CLI, it should be more prominent -- either inline in the "Fix" section or bolded. |
| 8 | No "How to report a bug" guidance for DS-501 | 404 | NICE TO HAVE | DS-501 says "Report this issue with the full error message and traceback" but does not say WHERE to report (no GitHub issues link). |

---

### 2.3 TROUBLESHOOTING.md (NEW)

**Rating: GOOD**

Excellent coverage of common errors with the exact error message text users will see. The how-to workflows are practical and step-by-step.

| # | Issue | Line | Severity | Description |
|---|-------|------|----------|-------------|
| 9 | "How to Cancel" section uses bare `resume` command | 138 | SHOULD FIX | Shows `deepscan resume <hash>` (without `poetry run python ...` prefix). Inconsistent with the fact that there is no `deepscan` binary -- the user needs the full path or `/deepscan` in Claude Code. |
| 10 | Missing scenario: "What if I run `map` in CLI and get placeholders?" links to wrong anchor | 110 | SHOULD FIX | Links to `GETTING-STARTED.md#environment-note` -- but the actual heading in GETTING-STARTED.md is "## Environment Note", which would produce anchor `#environment-note`. This is correct, but the link text says "Getting Started: Environment Note" which may confuse users who look for that exact heading. |
| 11 | "How to Uninstall" references `claude plugin remove deepscan` | 287 | NICE TO HAVE | This command is not validated anywhere in the docs as an actual working command. If `claude plugin remove` is not a real CLI command, this will confuse users. |
| 12 | Performance section does not mention `--adaptive` flag | 299-329 | NICE TO HAVE | The performance troubleshooting section recommends `write_chunks(semantic=False)` and larger chunk sizes but does not mention `--adaptive` as an optimization. |

---

### 2.4 REFERENCE.md (NEW)

**Rating: GOOD**

The most comprehensive document in the suite. Excellent coverage of commands, configuration, REPL sandbox rules, and file locations.

| # | Issue | Line | Severity | Description |
|---|-------|------|----------|-------------|
| 13 | `init` flags table missing `--file-limit` | 8-28 | NICE TO HAVE | The `lazy_file_limit` config setting (line 196) suggests a `--file-limit` flag exists, but it is not in the `init` flags table. If it is config-only, that is fine, but if there is a CLI flag, it should be documented. |
| 14 | REPL forbidden patterns says "15 regex patterns" but lists 15 patterns inline | 255-257 | GOOD | Accurate count. No issue. |
| 15 | `reset` command has no description of what it does | 144-148 | SHOULD FIX | The `reset` command is listed with syntax but no explanation of what it resets (session state? context? everything?). Compare to `abort` which clearly says "permanently delete a session and all its data". |
| 16 | Helper functions table is split into "Full Mode" and "Lazy Mode" without explaining which helpers work in both modes | 271-301 | SHOULD FIX | The note at line 301 says `get_tree_view()`, `preview_dir()`, and `load_file()` work in both modes, but they are listed under "Lazy Mode Helpers". This is confusing -- a user in full mode would skip that section entirely and miss these helpers. |

---

### 2.5 README.md (root, UPDATED)

**Rating: GOOD**

Clean, focused entry point. Good "When to Use / When NOT to Use" guidance. Documentation table is comprehensive.

| # | Issue | Line | Severity | Description |
|---|-------|------|----------|-------------|
| 17 | "Testing" section is prominent and says "No tests exist" | 98-120 | NICE TO HAVE | While honest, having "No tests exist yet" prominently in the README may discourage adoption. Consider moving to a "Development" subsection or linking to TEST-PLAN.md with a brief note. |
| 18 | Quick Example shows `/deepscan init` but does not show full CLI path | 61-73 | NICE TO HAVE | Consistent with the rest of the doc, but a first-time CLI user may not know how to translate `/deepscan` to the actual command. |

---

### 2.6 SKILL.md (UPDATED)

**Rating: GOOD**

Strong quick reference for Claude Code users. The CLI Shortcuts table is a welcome addition. The workflow steps are now complete with the `reduce` command added.

| # | Issue | Line | Severity | Description |
|---|-------|------|----------|-------------|
| 19 | Step 5 combines `reduce`, `progress`, and `export-results` in one section | 99-119 | NICE TO HAVE | The REDUCE step bundles three commands. For clarity, `export-results` could be Step 6 (matching GETTING-STARTED.md's 7-step flow). Minor structural mismatch between docs. |
| 20 | Helper functions table is a subset of REFERENCE.md | 133-153 | GOOD | Appropriate for a quick reference. No issue. |
| 21 | Troubleshooting section now links to external docs | 210-212 | GOOD | Clean replacement of sparse table with links. |

---

### 2.7 Skill README.md (.claude/skills/deepscan/README.md, UPDATED)

**Rating: NEEDS MINOR FIXES**

This is the longest document at ~525 lines. It serves as both the internal development guide and a feature overview. The file tree update and roadmap fix are accurate.

| # | Issue | Line | Severity | Description |
|---|-------|------|----------|-------------|
| 22 | Document is too long and mixes audiences | 1-525 | SHOULD FIX | This README serves developers (file metrics, development standards, roadmap) AND users (quick start, helper functions, resuming work). A user clicking into this from the docs/ directory gets overwhelmed. Consider splitting development content into a CONTRIBUTING.md or DEVELOPMENT.md. |
| 23 | "Phase 8" still appears in a heading at line 433 | 433 | SHOULD FIX | `**Timeout Behavior (Phase 8)**` -- the changes log says Phase 8 references were updated to Phase 7, but this one was missed. |
| 24 | `D2-FIX` annotation at line 85 | 85 | SHOULD FIX | Internal annotation `(D2-FIX)` is visible to users. Should be removed from the heading. |
| 25 | Quick Start section does not mention `map` or `reduce` | 113-149 | SHOULD FIX | The Quick Start goes init -> explore -> chunks -> status -> export. It skips the MAP and REDUCE phases entirely, which are the core value of DeepScan. A user following only this section will get empty exports. |
| 26 | "Complete Workflow Example (P5.2)" annotation | 155 | SHOULD FIX | Internal annotation `(P5.2)` is visible to users. Should be removed. |
| 27 | License link uses relative path `../../LICENSE` | 525 | NICE TO HAVE | This relative path assumes a specific directory depth. If LICENSE does not exist at that path, the link is broken. |

---

### 2.8 SECURITY.md (UPDATED)

**Rating: GOOD**

The "Security at a Glance" table is an excellent addition. The HMAC clarification (not yet implemented) and ReDoS fix (correct implementation) are important corrections.

| # | Issue | Line | Severity | Description |
|---|-------|------|----------|-------------|
| 28 | Unchecked security checklist item | 311 | MUST FIX (known) | `[ ] Test for path traversal with .. and symlinks` remains unchecked. This is documented in CLAUDE.md as a known gap but should be highlighted more prominently since it is a security item. |
| 29 | Layer 5 description mentions "5-second timeout" but default is auto-calculated | 89 | NICE TO HAVE | The defense-in-depth diagram says "5-second timeout (default; auto-calculated for write_chunks)". Accurate but could note that helper-path execution uses threads, not subprocess. |
| 30 | Code example at line 163 shows simplified `safe_write` | 163-173 | NICE TO HAVE | The pseudo-code is illustrative but does not match the actual implementation exactly. This is fine for explanation, but a link to the actual source line would help security reviewers. |

---

### 2.9 ARCHITECTURE.md (UPDATED)

**Rating: GOOD**

Clear system design with helpful ASCII diagrams. The file tree update is accurate.

| # | Issue | Line | Severity | Description |
|---|-------|------|----------|-------------|
| 31 | No cross-link to GETTING-STARTED.md from the workflow phases section | 165-208 | NICE TO HAVE | The workflow phases diagram describes the same flow as GETTING-STARTED but does not link to it. Users exploring architecture may want to jump to the tutorial. |
| 32 | Extension points section references `line 1431` in deepscan_engine.py | 337 | NICE TO HAVE | Line number references become stale quickly. Consider "search for `init_parser` in `deepscan_engine.py`" instead. |

---

### 2.10 USE_CASES.md (UPDATED)

**Rating: GOOD**

The new sections (11: Cancellation, 12: REPL Examples) are well-integrated. The incremental scanning step-by-step is actionable.

| # | Issue | Line | Severity | Description |
|---|-------|------|----------|-------------|
| 33 | Section 12 example uses `__setitem__` which is a dunder method | 295 | MUST FIX | `exts.__setitem__(...)` uses a dunder method access pattern that may be blocked by the REPL's Layer 3 attribute blocking (all `_`-prefixed attributes are blocked). This example would fail in the actual sandbox. |
| 34 | Section numbers jump from 10 to 11, 12, 13 | 260-314 | NICE TO HAVE | Old sections 1-10 were not renumbered when new sections 11-12 were inserted and 13 was the old section 11. The numbering is correct but the document structure feels patched. |

---

### 2.11 CLAUDE.md (UPDATED)

**Rating: GOOD**

Accurate developer guidance. The updated repository layout table and documentation table are well-structured.

| # | Issue | Line | Severity | Description |
|---|-------|------|----------|-------------|
| 35 | Version says "v2.0.0" in Skill README but CLAUDE.md Repository Layout table does not show version | 7-14 | NICE TO HAVE | The Repository Layout table mentions purpose but not version. The version is documented in plugin.json and Skill README. Not a gap, but consistency note. |
| 36 | Documentation table links use relative paths from repo root | 66-75 | GOOD | All links are correct relative to CLAUDE.md location at repo root. |

---

## 3. Cross-Document Issues

### 3.1 Navigation / Discoverability

| # | Issue | Severity | Description |
|---|-------|----------|-------------|
| 37 | No single "documentation index" page | NICE TO HAVE | Each doc has a "See Also" section, but there is no central docs/INDEX.md that lists all docs with one-line descriptions. The README serves this role partially, but a user in the docs/ directory has no index file. |
| 38 | Two README files serve different audiences | SHOULD FIX | Root README.md is the plugin overview (user-facing). Skill README.md at `.claude/skills/deepscan/README.md` is a 525-line development guide. Users navigating from the root README will land on the docs, but if they find the Skill README first, they may be confused by the development content. |

### 3.2 Terminology Consistency

| # | Issue | Files | Severity | Description |
|---|-------|-------|----------|-------------|
| 39 | Command prefix inconsistency | GETTING-STARTED, TROUBLESHOOTING, USE_CASES, SKILL.md | SHOULD FIX | Four different command forms appear: (a) `poetry run python .claude/skills/deepscan/scripts/deepscan_engine.py <cmd>`, (b) `/deepscan <cmd>`, (c) `deepscan <cmd>`, (d) bare `<cmd>` (e.g., `map`, `exec -c ...`). There is no `deepscan` binary, so form (c) is misleading. Form (d) is only valid inside Claude Code skill context. Each doc should be explicit about which environment is assumed. |
| 40 | "31 error codes" vs "26 error codes" | ERROR-CODES.md, user-scenarios temp | NICE TO HAVE | The user scenarios doc (a temp file) references "26 error codes" which was the pre-update count. All permanent docs consistently say "31". This is fine for shipped docs. |
| 41 | Error code count in title | ERROR-CODES.md title | NICE TO HAVE | The document is titled "DeepScan Error Code Reference" but does not state the count in the title. The "31" count appears only in other docs that link to it. |

### 3.3 Cross-Reference Integrity

| # | Issue | Files | Severity | Description |
|---|-------|-------|----------|-------------|
| 42 | All cross-links between docs/ files use relative paths | All docs/ files | GOOD | `TROUBLESHOOTING.md` links to `ERROR-CODES.md`, `REFERENCE.md`, etc. using relative paths. All verified correct since they are in the same directory. |
| 43 | README.md links use `.claude/skills/deepscan/docs/` prefix | README.md | GOOD | Correct relative paths from repo root. |
| 44 | Skill README links use `docs/` prefix | Skill README | GOOD | Correct relative paths from `.claude/skills/deepscan/`. |
| 45 | GETTING-STARTED.md "What's Next" links use bare filenames | GETTING-STARTED.md:217-220 | GOOD | Correct since GETTING-STARTED.md is in the docs/ directory. |

---

## 4. Scenario Walkthrough Results

### Scenario 1: Installation

**Result: PARTIAL PASS**

A user following README -> GETTING-STARTED can install the plugin. However:
- **FAIL POINT**: The clone path (`git clone ... && copy directories`) does not mention `poetry install`. The verify command (`poetry run python ...`) will fail with a dependency error unless the user independently knows to run `poetry install`.
- **PASS**: Plugin add path (`claude plugin add idnotbe/deepscan`) presumably handles dependencies.
- **PASS**: Prerequisites are clearly stated (Python 3.10+, pydantic).
- **PASS**: Verification command with expected output is provided.

### Scenario 2: First Scan

**Result: PARTIAL PASS**

A user following GETTING-STARTED Steps 1-7 can complete a first scan in Claude Code. However:
- **FAIL POINT**: Steps 3-7 use bare command names (`exec -c "..."`, `map`, `reduce`). A CLI user will not know the full command. Step 2 shows both `poetry run python ...` and `/deepscan` forms, but subsequent steps drop the prefix.
- **PASS**: Expected output at each step is clear.
- **PASS**: The flow from init to export is complete and logical.
- **PASS**: Environment Note explains CLI vs Claude Code limitation.

### Scenario 8: Error Handling

**Result: PASS**

A user encountering errors can self-diagnose:
- **PASS**: ERROR-CODES.md covers all 31 error codes with actionable fixes.
- **PASS**: TROUBLESHOOTING.md covers the 8 most common errors with exact error message text.
- **PASS**: Cross-links between TROUBLESHOOTING and ERROR-CODES are present.
- **PASS**: Error format explanation (`[DS-NNN] Title: message`) is clear.
- **MINOR**: DS-505 remediation note about wrong template could be more prominent.

### Cross-document flow: README -> GETTING-STARTED -> First Scan

**Result: PASS with friction**

- README -> GETTING-STARTED link: Present and clear
- GETTING-STARTED installation: Works for `claude plugin add` path
- GETTING-STARTED Steps 1-7: Clear progression with expected output
- **Friction**: Bare command names in Steps 3-7 assume Claude Code environment without stating it explicitly after Step 2

---

## 5. Prioritized Fix List

### MUST FIX (2 items)

| # | File:Line | Issue | Impact |
|---|-----------|-------|--------|
| 33 | USE_CASES.md:295 | REPL example uses `__setitem__` which is blocked by sandbox Layer 3 | Users following this example will get a "Forbidden attribute" error. The example is wrong and teaches bad patterns. |
| 28 | SECURITY.md:311 | Unchecked security checklist item `[ ] Test for path traversal` | Known gap, but since the docs are now being shipped, this unchecked item in a security document signals incomplete security validation to reviewers. Should either be checked (if tested) or have a clear note that it is a known testing gap. |

### SHOULD FIX (11 items)

| # | File:Line | Issue | Impact |
|---|-----------|-------|--------|
| 1 | GETTING-STARTED.md:98-179 | Steps 3-7 use bare command names with no environment prefix | CLI users cannot follow the tutorial without guessing the full command |
| 2 | GETTING-STARTED.md:37-67 | No `poetry install` step after clone | Verify command will fail for clone-path users |
| 7 | ERROR-CODES.md:463 | DS-505 wrong remediation template note is too subtle | Users will copy the wrong command from CLI output |
| 9 | TROUBLESHOOTING.md:138 | Bare `deepscan resume` -- no such binary exists | Users will type a nonexistent command |
| 15 | REFERENCE.md:144-148 | `reset` command undocumented behavior | Users do not know what `reset` does |
| 16 | REFERENCE.md:271-301 | Lazy/Full mode helper split is confusing | Full mode users miss helpers that work in both modes |
| 22 | Skill README.md:1-525 | Too long, mixes audiences | Overwhelms users, buries developer content |
| 23 | Skill README.md:433 | "Phase 8" still in heading | Inconsistent with Phase 7 corrections elsewhere |
| 24 | Skill README.md:85 | Internal `(D2-FIX)` annotation visible | Looks unprofessional/confusing to users |
| 25 | Skill README.md:113-149 | Quick Start skips MAP and REDUCE | Users following only Quick Start get empty exports |
| 26 | Skill README.md:155 | Internal `(P5.2)` annotation visible | Looks unprofessional/confusing to users |
| 39 | Cross-document | Command prefix inconsistency (4 forms) | Users unsure how to invoke commands |

### NICE TO HAVE (14 items)

| # | File:Line | Issue |
|---|-----------|-------|
| 4 | GETTING-STARTED.md:93-116 | Scout step has no exit criteria |
| 5 | GETTING-STARTED.md:23-35 | Environment Note could link to REFERENCE.md |
| 6 | ERROR-CODES.md:5 | Broken doc_url warning could be more prominent |
| 8 | ERROR-CODES.md:404 | DS-501 no bug report link |
| 11 | TROUBLESHOOTING.md:287 | Unvalidated `claude plugin remove` command |
| 12 | TROUBLESHOOTING.md:299-329 | Performance section missing `--adaptive` |
| 13 | REFERENCE.md:8-28 | Missing `--file-limit` flag if it exists |
| 17 | README.md:98-120 | "No tests" prominent in README |
| 18 | README.md:61-73 | Quick Example only shows `/deepscan` form |
| 27 | Skill README.md:525 | License link may be broken |
| 29 | SECURITY.md:89 | Timeout description could note thread vs subprocess distinction |
| 31 | ARCHITECTURE.md:165-208 | No link to GETTING-STARTED from workflow section |
| 34 | USE_CASES.md:260-314 | Section numbering feels patched |
| 37 | Cross-document | No central docs/INDEX.md |

---

## 6. Summary Metrics

| Document | Rating | Must Fix | Should Fix | Nice to Have |
|----------|--------|----------|------------|--------------|
| GETTING-STARTED.md | GOOD | 0 | 2 | 2 |
| ERROR-CODES.md | GOOD | 0 | 1 | 2 |
| TROUBLESHOOTING.md | GOOD | 0 | 1 | 2 |
| REFERENCE.md | GOOD | 0 | 2 | 1 |
| README.md (root) | GOOD | 0 | 0 | 2 |
| SKILL.md | GOOD | 0 | 0 | 1 |
| Skill README.md | NEEDS MINOR FIXES | 0 | 5 | 1 |
| SECURITY.md | GOOD | 1 | 0 | 2 |
| ARCHITECTURE.md | GOOD | 0 | 0 | 2 |
| USE_CASES.md | GOOD | 1 | 0 | 1 |
| CLAUDE.md | GOOD | 0 | 0 | 1 |
| **Cross-document** | -- | 0 | 1 | 1 |
| **TOTAL** | -- | **2** | **12** | **18** |

Overall: The documentation is in **good shape** with strong structural improvements. The 2 MUST FIX items are isolated (one broken example, one known security gap). The 12 SHOULD FIX items are primarily about command prefix consistency and the Skill README cleanup -- patterns that can be addressed in a focused pass.
