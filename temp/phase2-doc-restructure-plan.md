# Phase 2: Documentation Restructuring Plan

> Generated: 2026-02-16
> Inputs: Phase 1 scenario analysis (32 scenarios), Phase 2 best practices research
> Purpose: Actionable plan for the doc-writer teammate in Phase 3

---

## 1. Executive Summary

The current documentation is organized by **system component** (ARCHITECTURE.md, SECURITY.md, SKILL.md). The 32 user scenarios from Phase 1 reveal that users think in **tasks and journeys**, not components. The restructuring applies the Diataxis framework to reorganize around four documentation types: Tutorial, How-To, Reference, Explanation.

**Scope of changes:**
- 4 new files to create
- 4 existing files to update
- 2 existing files to leave as-is
- 0 files to delete

---

## 2. Current State

### Existing Documentation Files

| File | Path | Lines | Diataxis Type | Status |
|------|------|-------|---------------|--------|
| README.md | `/README.md` | 104 | Gateway (mixed) | UPDATE |
| SKILL.md | `/.claude/skills/deepscan/SKILL.md` | 210 | Reference | UPDATE |
| ARCHITECTURE.md | `/.claude/skills/deepscan/docs/ARCHITECTURE.md` | 365 | Explanation | UPDATE (minor) |
| SECURITY.md | `/.claude/skills/deepscan/docs/SECURITY.md` | 296 | Explanation | UPDATE |
| USE_CASES.md | `/.claude/skills/deepscan/docs/USE_CASES.md` | 262 | How-To | KEEP AS-IS |
| ADR-001-*.md | `/.claude/skills/deepscan/docs/ADR-001-*.md` | ~100 | Explanation | KEEP AS-IS |
| CLAUDE.md | `/CLAUDE.md` | ~90 | Developer guide | KEEP AS-IS |
| TEST-PLAN.md | `/TEST-PLAN.md` | ~200 | Developer guide | KEEP AS-IS |

### New Files to Create

| File | Path | Diataxis Type | Primary Persona |
|------|------|---------------|-----------------|
| GETTING-STARTED.md | `/.claude/skills/deepscan/docs/GETTING-STARTED.md` | Tutorial | P1 (Beginner) |
| TROUBLESHOOTING.md | `/.claude/skills/deepscan/docs/TROUBLESHOOTING.md` | How-To | P1, P2 |
| ERROR-CODES.md | `/.claude/skills/deepscan/docs/ERROR-CODES.md` | Reference | P2 |
| REFERENCE.md | `/.claude/skills/deepscan/docs/REFERENCE.md` | Reference | P2 |

### Final File Tree

```
deepscan/
  README.md                                    # Gateway
  CLAUDE.md                                    # Developer/contributor (unchanged)
  TEST-PLAN.md                                 # Test planning (unchanged)
  .claude-plugin/plugin.json                   # Plugin manifest (unchanged)
  .claude/skills/deepscan/
    SKILL.md                                   # Skill interface + quick reference
    docs/
      GETTING-STARTED.md                       # NEW: Tutorial
      TROUBLESHOOTING.md                       # NEW: How-To (error recovery)
      ERROR-CODES.md                           # NEW: Reference (error codes)
      REFERENCE.md                             # NEW: Reference (commands/config/REPL)
      USE_CASES.md                             # How-To (advanced, unchanged)
      ARCHITECTURE.md                          # Explanation (minor updates)
      SECURITY.md                              # Explanation (add user summary)
      ADR-001-repl-security-relaxation.md      # Explanation (unchanged)
```

---

## 3. New Files: Detailed Specifications

### 3.1 GETTING-STARTED.md (Tutorial)

**Purpose:** Take a beginner from zero to their first complete scan result.

**Diataxis rules for tutorials:**
- Hand-hold the reader through every step
- Every step must produce a visible result
- Make no assumptions about prior knowledge
- Don't offer choices -- decide for the reader

**Target length:** 200-300 lines

**Scope fallback:** If the tutorial exceeds 300 lines, cut Steps 6-7 (Reduce/Export) into a brief "next step" link rather than fully documenting them. The minimum viable tutorial ends at Step 5 (MAP) -- the user has seen DeepScan work.

**Outline:**

```markdown
# Getting Started with DeepScan

## What You'll Accomplish
[1-2 sentences: "By the end, you'll have scanned a project and
reviewed findings with file:line evidence."]

## Prerequisites
- Claude Code installed and working
- Python 3.10+ (`python3 --version` to check)
- A project with 10+ source files to scan

## Environment Note
[CRITICAL: Explain CLI vs Claude Code distinction HERE, before anything else]
- DeepScan has two modes: CLI (exploration) and Claude Code (full analysis)
- Table showing which commands work where
- MAP phase requires Claude Code environment -- CLI produces placeholders

## Step 1: Install DeepScan
- Plugin install command
- Verification command + expected output

## Step 2: Initialize a Scan
- `/deepscan init ./src -q "Find security vulnerabilities"`
- Expected output (show real output format)
- What happened: "DeepScan loaded N files totaling X characters"

## Step 3: Explore with Scout
- `exec -c "print(peek_head(5000))"`
- Expected output
- What to look for

## Step 4: Create Chunks
- `exec -c "paths = write_chunks(size=150000); print(f'{len(paths)} chunks')"`
- Expected output
- What happened: "Your context was split into N manageable pieces"

## Step 5: Run MAP Phase (Claude Code)
- `map`
- Expected output
- Note: If in CLI, you'll see placeholder results
- For manual mode: `map --instructions`

## Step 6: Reduce and Review
- `reduce` (or `export-results output.json`)
- Show a real finding example with point/evidence/confidence/location
- How to navigate to source: "Open app.py at line 45"

## Step 7: Export Results
- `export-results findings.json`
- Brief description of JSON structure

## What's Next
- [How to scan incrementally](TROUBLESHOOTING.md) (link to relevant how-to)
- [Advanced use cases](USE_CASES.md) -- lazy mode, targeted, incremental
- [Full command reference](REFERENCE.md)
- [REPL sandbox rules](REFERENCE.md#repl-sandbox)
```

**Scenarios addressed:** 1.1, 1.2, 2.2, 3.1, 3.3, 4.1, 12.1, 13.1

---

### 3.2 TROUBLESHOOTING.md (How-To)

**Purpose:** Answer "How do I fix this?" for common problems and workflows.

**Diataxis rules for how-to guides:**
- Start with the goal, not background
- Assume baseline knowledge
- Be practical and actionable
- Each section is self-contained

**Diataxis note:** This file deliberately blends error lookup (Reference-flavored) with workflow guides (How-To). This is a practical choice -- users hitting errors want both the diagnosis and the fix in one place. Strict Diataxis would split these, but findability wins over purity here.

**Target length:** 300-400 lines

**Outline:**

```markdown
# Troubleshooting & How-To Guides

## Common Errors

### "No state found" / DS-306
- What it means
- Fix: Run `init` first, or `list` to find existing sessions
- Link to ERROR-CODES.md#ds-306

### "Forbidden pattern" / "Forbidden AST node"
- What it means: sandbox blocked your code
- Common examples that trigger this
- What IS allowed (quick table, link to REFERENCE.md#repl-sandbox)
- Fix: Use built-in helpers instead

### "Active session already exists"
- What it means: overwrite protection
- Fix: Use `--force` flag, or `resume` the existing session

### "Execution timed out" / DS-503
- What it means
- Fix: Use `--timeout` flag, or reduce chunk size
- Link to ERROR-CODES.md#ds-503

### "File too large" / DS-303
- What it means: single file exceeds 10MB
- Fix: File is auto-skipped. Use `.deepscanignore` to explicitly exclude
- Link to ERROR-CODES.md#ds-303

### "Context too large" / DS-304
- What it means: total context exceeds 50MB
- Fix: Use `--lazy` or `--target` to reduce scope

### "All results are placeholders"
- What it means: MAP ran in CLI mode, not Claude Code
- Fix: Run `/deepscan map` in Claude Code environment
- Link to GETTING-STARTED.md#environment-note

## How-To Workflows

### How to Cancel a Running Scan
- Ctrl+C: graceful shutdown (saves progress)
- Double Ctrl+C: force quit
- Progress is checkpointed -- resume with `resume [hash]`
- Link to ERROR-CODES.md#ds-505

### How to Resume an Interrupted Scan
- After Ctrl+C, crash, or network issue
- `list` to find session hash
- `resume <hash>` to continue
- In-progress chunks are re-queued

### How to Scan Incrementally
- Step-by-step: first full scan, then incremental
- `init <path> --incremental --previous-session <hash>`
- How to find previous session hash: `list`
- What gets re-analyzed (changed/added files)

### How to Exclude Files (.deepscanignore)
- Create `.deepscanignore` in project root
- Pattern syntax (directory names, glob patterns)
- Example file
- Link to USE_CASES.md#10 for details

### How to Use MAP Instructions Mode
- When to use: manual control over sub-agent execution
- `map --instructions` to get prompts
- How to execute with Task tool
- How to feed results back with `add_result()`

### How to Uninstall DeepScan
- Remove plugin registration
- Clean up cache: `rm -rf ~/.claude/cache/deepscan/`
- Verify removal

## Platform-Specific Issues

### Windows
- Set `$env:PYTHONIOENCODING='utf-8'`
- Resource limits (memory/CPU) are NOT enforced on Windows
- The `resource` module is unavailable -- sandbox runs with degraded protection
```

**Scenarios addressed:** 6.1, 6.2, 6.3, 6.4, 6.5, 7.1, 8.1, 9.2, 10.1, 12.2, 17.1, 20.1, 21.1, 21.2

---

### 3.3 ERROR-CODES.md (Reference)

**Purpose:** Searchable reference for every DeepScan error code.

**Pattern:** Follows the Rust error index model -- each code has its own heading with description, common causes, and fix.

**Target length:** 200-300 lines

**Source data:** Extract directly from `error_codes.py` (lines 60-101 for codes, lines 218-305 for remediation templates).

**Outline:**

```markdown
# DeepScan Error Code Reference

## Error Code Format
- Display format: `[DS-NNN] Title: message`
- Categories: DS-0xx (Validation), DS-1xx (Parsing), DS-2xx (Chunking),
  DS-3xx (Resource), DS-4xx (Configuration), DS-5xx (System)

## Exit Codes
| Category | Exit Code |
|----------|-----------|
| Validation (DS-0xx) | 2 |
| Parsing (DS-1xx) | 3 |
| Chunking (DS-2xx) | 4 |
| Resource (DS-3xx) | 5 |
| Configuration (DS-4xx) | 6 |
| System (DS-5xx) | 1 |
| Cancelled (DS-505) | 130 (SIGINT convention) |

---

## DS-0xx: Input / Validation

### DS-001: Invalid Context Path
[Description, common causes, fix -- extracted from REMEDIATION_TEMPLATES]

### DS-002: Invalid Session Hash
...

### DS-003: Missing Query
...

### DS-004: Invalid Chunk Size
...

### DS-005: Overlap Exceeds Size
...

### DS-006: Empty Context
...

## DS-1xx: Parsing / Processing

### DS-101: AST Parse Failed
...

### DS-102: JSON Decode Error
...

[Continue for all 25 error codes]

## DS-5xx: System / Internal

### DS-505: Cancelled By User
- Exit code: 130 (Unix SIGINT convention)
- Progress is checkpointed automatically
- Resume: `resume <session_hash>`
```

**Each entry format:**
```markdown
### DS-NNN: Title
**Category:** Validation | Parsing | Chunking | Resource | Config | System
**Exit code:** N

**What happened:** [1-2 sentences explaining the error]

**Common causes:**
- [Cause 1]
- [Cause 2]

**Fix:** [Extracted from REMEDIATION_TEMPLATES, with concrete actions]
```

**Scenarios addressed:** 6.1, 6.2, 6.4, 6.5, 20.1

---

### 3.4 REFERENCE.md (Reference)

**Purpose:** Complete lookup reference for all commands, configuration, REPL sandbox, and file locations.

**Diataxis rules for reference:**
- Mirror the structure of the thing being described
- Be austere -- no narrative, no persuasion
- Complete -- every command, every flag, every default
- Organized for lookup, not linear reading

**Target length:** 300-400 lines

**Outline:**

```markdown
# DeepScan Reference

## Commands

### init
[Synopsis, all flags with types/defaults/descriptions, examples]

### scout / exec
[Synopsis, flags, examples]

### map
[Synopsis, flags including --escalate, --instructions, --batch, --limit, --output]

### reduce / export-results
[Synopsis, flags, output format]

### resume
[Synopsis, flags]

### list / status / progress
[Synopsis, flags]

### abort / clean
[Synopsis, flags]

## CLI Shortcuts
| Shortcut | Expands to | Description |
|----------|------------|-------------|
| `?` | `status` | Show current session status |
| `!` | `exec` | Execute REPL expression |
| `+` | `resume` | Resume last session |
| `x` | `abort` | Abort current session |
| `<path>` | `init <path>` | Initialize scan on path |

## CLI vs Claude Code Environment

| Feature | CLI | Claude Code |
|---------|-----|-------------|
| init (load context) | Yes | Yes |
| scout (peek, grep) | Yes | Yes |
| chunk (write_chunks) | Yes | Yes |
| map (parallel analysis) | Placeholders only | Full sub-agent processing |
| reduce (aggregate) | Placeholders only | Real aggregation |
| export-results | Yes | Yes |
| progress / status | Yes | Yes |
| Natural language triggers | No | Yes |

## Configuration Settings

| Setting | Default | Range | CLI Flag | Description |
|---------|---------|-------|----------|-------------|
| chunk_size | 150000 | 50K-300K | `--chunk-size` | Characters per chunk |
| chunk_overlap | 0 | 0 to chunk_size/2 | `--overlap` | Overlap between chunks |
| max_parallel_agents | 5 | 1-20 | N/A | Sub-agents per batch |
| timeout_seconds | 300 | 30-3600 | `--timeout` | Sub-agent timeout |
| enable_escalation | true | boolean | `--escalate` | haiku -> sonnet on failure |
| agent_type | general | general/security/architecture/performance | `--agent-type` | Analysis specialization |
| adaptive | false | boolean | `--adaptive` | Content-type chunk sizing |
| lazy | false | boolean | `--lazy` | Structure-only mode |

## Specialized Agent Types

| Type | Flag | Focus | Example Query |
|------|------|-------|---------------|
| general | `--agent-type general` | Broad analysis | "Review code quality" |
| security | `--agent-type security` | Vulnerabilities, credentials | "Find SQL injection, XSS" |
| architecture | `--agent-type architecture` | Design, coupling, deps | "Find circular dependencies" |
| performance | `--agent-type performance` | Bottlenecks, complexity | "Find N+1 queries, nested loops" |

## REPL Sandbox

### Allowed Operations
| Category | Examples |
|----------|----------|
| Arithmetic | `+`, `-`, `*`, `/`, `//`, `%`, `**` |
| Comparisons | `==`, `!=`, `<`, `>`, `<=`, `>=` |
| Boolean | `and`, `or`, `not` |
| String ops | `str.upper()`, `str.split()`, f-strings |
| Collections | `list`, `dict`, `set`, `tuple` operations |
| Comprehensions | `[x for x in data]`, `{k: v for ...}` |
| Lambda | `lambda x: x > 0` |
| Ternary | `x if cond else y` |
| Built-in helpers | `peek()`, `grep()`, `write_chunks()`, etc. |
| Safe builtins | `len`, `str`, `int`, `print`, `sorted`, `enumerate`, `zip`, `map`, `filter`, `range`, `type`, `isinstance`, `dir`, `vars`, `hasattr`, `min`, `max`, `sum`, `abs`, `round`, `any`, `all`, `reversed`, `list`, `dict`, `set`, `tuple`, `bool`, `float`, `complex`, `frozenset`, `bytes`, `bytearray`, `memoryview`, `slice`, `iter`, `next`, `repr`, `chr`, `ord`, `hex`, `oct`, `bin`, `ascii`, `hash` |

### Blocked Operations
| Category | Examples | Reason |
|----------|----------|--------|
| Imports | `import os`, `__import__('os')` | System access |
| Dynamic dispatch | `getattr()`, `setattr()`, `delattr()` | Bypasses AST filtering |
| Code execution | `exec()`, `eval()`, `compile()` | Arbitrary code |
| Dunder access | `__class__`, `__globals__`, `__bases__` | Sandbox escape |
| Function/class defs | `def func():`, `class Foo:` | Hidden complexity |
| File I/O | `open()`, `Path.write_text()` | Filesystem access |
| Format string abuse | `format()` built-in | Can access object internals |

## Helper Functions

### Full Mode Helpers
[Table: function signature, description, return type]

### Lazy Mode Helpers
[Table: function signature, description, return type]

## File Locations

| File | Path | Purpose |
|------|------|---------|
| Session state | `~/.claude/cache/deepscan/{hash}/state.json` | Main state |
| Checkpoint | `~/.claude/cache/deepscan/{hash}/checkpoint.json` | Recovery |
| Chunks | `~/.claude/cache/deepscan/{hash}/chunks/` | Chunk files |
| Results | `~/.claude/cache/deepscan/{hash}/results/` | Sub-agent results |
| Progress | `~/.claude/cache/deepscan/{hash}/progress.jsonl` | Real-time log |

## Model Escalation

| Parameter | Value |
|-----------|-------|
| Default model | haiku |
| Escalation model | sonnet |
| Max escalated chunks | 15% of total |
| Sonnet budget cap | $5 |
| Trigger | Quality failure or complexity flag |

## Natural Language Triggers
[List from SKILL.md frontmatter: "analyze large codebase", "security audit across", etc.]
```

**Scenarios addressed:** 2.1, 3.3, 5.1, 5.2, 9.2, 9.3, 12.3, 19.1

---

## 4. Existing Files: Update Specifications

### 4.1 README.md -- UPDATE

**Current issues:**
- Missing prerequisites (Python 3.10+, poetry, pydantic)
- Missing installation verification step
- Missing example output (what does a finding look like?)
- Testing section is prominent but discouraging for users ("No tests exist yet")
- No link to GETTING-STARTED.md

**Changes:**

| Section | Action | Detail |
|---------|--------|--------|
| Installation | ADD prerequisites | Python 3.10+, poetry, pydantic; verification command |
| Usage | ADD example output | Show a real finding with point/evidence/confidence/location |
| Usage | ADD link | "See [Getting Started](/.claude/skills/deepscan/docs/GETTING-STARTED.md) for a complete walkthrough" |
| Testing | MOVE down | Below Documentation section; less prominent position |
| Documentation | ADD links | GETTING-STARTED.md, TROUBLESHOOTING.md, ERROR-CODES.md, REFERENCE.md |

**Scenarios addressed:** 1.1, 1.2, 2.2, 4.1

---

### 4.2 SKILL.md -- UPDATE

**Current issues:**
- CLI vs Claude Code distinction exists but is scattered (lines 44-46, 57-58)
- No CLI shortcuts documented
- Troubleshooting table (lines 198-203) is too sparse -- should link to TROUBLESHOOTING.md
- No link to new documentation files

**Changes:**

| Section | Action | Detail |
|---------|--------|--------|
| Quick Reference table | ADD column | "Environment" column already exists -- verify clarity |
| After Quick Reference | ADD section | "CLI Shortcuts" table: `?`, `!`, `+`, `x`, path shortcut |
| Troubleshooting | REPLACE | Replace sparse 4-row table with link: "See [Troubleshooting](docs/TROUBLESHOOTING.md) for error recovery guides and [Error Codes](docs/ERROR-CODES.md) for the full error reference." |
| References | ADD links | GETTING-STARTED.md, TROUBLESHOOTING.md, ERROR-CODES.md, REFERENCE.md |
| Top note | ENHANCE | Make CLI vs Claude Code warning more specific: link to REFERENCE.md#cli-vs-claude-code |

**Line budget:** Currently 210 lines. Changes should keep it under 250. Well under the 500-line Claude Code skill convention.

**Scenarios addressed:** 3.3, 19.1, 6.1, 6.2

---

### 4.3 SECURITY.md -- UPDATE

**Current issues:**
- Excellent for security audience (P3) but impenetrable for beginners
- No user-friendly summary at top
- Testing checklist items mixed into security docs (line 278)

**Changes:**

| Section | Action | Detail |
|---------|--------|--------|
| Top (after title) | ADD section | "Security at a Glance" -- 10-15 lines summarizing the three layers, what's allowed, what's blocked, in plain language |
| Section 3 | ADD cross-link | Link to REFERENCE.md#repl-sandbox for the user-facing allowed/blocked tables |
| Section 9 checklist | ADD note | "See TEST-PLAN.md for testing status" |
| Known Limitations (3.3) | ADD mitigation guidance | Docker `--memory` flag, running in container for production |

**Scenarios addressed:** 9.2, 14.1, 14.2

---

### 4.4 ARCHITECTURE.md -- UPDATE (minor)

**Current issues:**
- Missing cross-links to new documentation files
- References section is sparse

**Changes:**

| Section | Action | Detail |
|---------|--------|--------|
| References (bottom) | ADD links | GETTING-STARTED.md, REFERENCE.md, ERROR-CODES.md |
| Section 4.2 Error Recovery | ADD link | "See [Error Codes](ERROR-CODES.md) for the complete error reference" |

**Scenarios addressed:** None directly -- this is a navigation improvement.

---

## 5. Scenario-to-Document Mapping

This table maps all 32 scenarios from Phase 1 to their target documentation location after restructuring.

### Scenario Group 1: Discovery & Installation

| Scenario | ID | Priority | Target Document | Section |
|----------|----|----------|-----------------|---------|
| Finding the Plugin | 1.1 | HIGH | README.md | What It Does + example output |
| Installing the Plugin | 1.2 | HIGH | README.md + GETTING-STARTED.md | Prerequisites + Step 1 |
| Plugin vs Skill Architecture | 1.3 | MEDIUM | GETTING-STARTED.md | Environment Note |

### Scenario Group 2: First-Time Setup

| Scenario | ID | Priority | Target Document | Section |
|----------|----|----------|-----------------|---------|
| Pre-Scan Configuration | 2.1 | MEDIUM | REFERENCE.md | Configuration Settings |
| Environment Requirements | 2.2 | HIGH | GETTING-STARTED.md + README.md | Prerequisites |

### Scenario Group 3: Running First Scan

| Scenario | ID | Priority | Target Document | Section |
|----------|----|----------|-----------------|---------|
| Quick Start - Small Project | 3.1 | HIGH | GETTING-STARTED.md | Steps 2-7 |
| Natural Language Triggers | 3.2 | MEDIUM | REFERENCE.md | Natural Language Triggers |
| CLI vs Claude Code Split | 3.3 | HIGH | GETTING-STARTED.md + REFERENCE.md + SKILL.md | Environment Note + CLI vs Claude Code table |

### Scenario Group 4: Understanding Results

| Scenario | ID | Priority | Target Document | Section |
|----------|----|----------|-----------------|---------|
| Interpreting Scan Output | 4.1 | HIGH | GETTING-STARTED.md + README.md | Step 6 + example output |
| Exporting Results | 4.2 | MEDIUM | REFERENCE.md | export-results command |
| Dedup & Contradiction | 4.3 | LOW | ARCHITECTURE.md | Section 3.5 (exists) |

### Scenario Group 5: Configuration Tuning

| Scenario | ID | Priority | Target Document | Section |
|----------|----|----------|-----------------|---------|
| Chunk Size Optimization | 5.1 | LOW | REFERENCE.md + USE_CASES.md | Configuration + Section 3 |
| Agent Type Selection | 5.2 | MEDIUM | REFERENCE.md | Specialized Agent Types |
| Custom Ignore Patterns | 5.3 | LOW | TROUBLESHOOTING.md + USE_CASES.md | How to Exclude Files + Section 10 |

### Scenario Group 6: Error Recovery

| Scenario | ID | Priority | Target Document | Section |
|----------|----|----------|-----------------|---------|
| "No State Found" | 6.1 | HIGH | TROUBLESHOOTING.md + ERROR-CODES.md | Common Errors + DS-306 |
| "Forbidden Pattern" | 6.2 | HIGH | TROUBLESHOOTING.md + REFERENCE.md | Common Errors + REPL Sandbox |
| Session Overwrite | 6.3 | MEDIUM | TROUBLESHOOTING.md | "Active session already exists" |
| Timeout Errors | 6.4 | MEDIUM | TROUBLESHOOTING.md + ERROR-CODES.md | Common Errors + DS-503 |
| File/Context Too Large | 6.5 | MEDIUM | TROUBLESHOOTING.md + ERROR-CODES.md | Common Errors + DS-303/DS-304 |

### Scenario Group 7: Incremental Scanning

| Scenario | ID | Priority | Target Document | Section |
|----------|----|----------|-----------------|---------|
| Setting Up Incremental | 7.1 | MEDIUM | TROUBLESHOOTING.md | How to Scan Incrementally |
| Delta Detection | 7.2 | LOW | ARCHITECTURE.md | (existing content sufficient) |

### Scenario Group 8: Checkpoint/Resume

| Scenario | ID | Priority | Target Document | Section |
|----------|----|----------|-----------------|---------|
| Resuming Interrupted Scan | 8.1 | HIGH | TROUBLESHOOTING.md | How to Resume |
| Managing Multiple Sessions | 8.2 | LOW | REFERENCE.md | list/resume commands |

### Scenario Group 9: REPL Usage

| Scenario | ID | Priority | Target Document | Section |
|----------|----|----------|-----------------|---------|
| Exploring with Helpers | 9.1 | MEDIUM | GETTING-STARTED.md + REFERENCE.md | Step 3 + Helper Functions |
| Sandbox Restrictions | 9.2 | HIGH | REFERENCE.md + TROUBLESHOOTING.md | REPL Sandbox + Forbidden Pattern |
| Custom Analysis | 9.3 | MEDIUM | REFERENCE.md | REPL Sandbox (allowed operations) |

### Scenario Group 10-11: Lazy & Targeted Mode

| Scenario | ID | Priority | Target Document | Section |
|----------|----|----------|-----------------|---------|
| Lazy Mode Exploration | 10.1 | MEDIUM | USE_CASES.md | Section 1 (exists) |
| Loading Files in Lazy | 10.2 | MEDIUM | USE_CASES.md | Section 1 (exists) |
| Targeted Analysis | 11.1 | MEDIUM | USE_CASES.md | Section 1 (exists) |

### Scenario Group 12-13: MAP & REDUCE

| Scenario | ID | Priority | Target Document | Section |
|----------|----|----------|-----------------|---------|
| MAP in Claude Code | 12.1 | HIGH | GETTING-STARTED.md | Step 5 |
| MAP Instructions Mode | 12.2 | HIGH | TROUBLESHOOTING.md | How to Use MAP Instructions |
| Model Escalation | 12.3 | MEDIUM | REFERENCE.md | Model Escalation |
| REDUCE Phase | 13.1 | HIGH | GETTING-STARTED.md | Step 6 |

### Scenario Group 14: Security

| Scenario | ID | Priority | Target Document | Section |
|----------|----|----------|-----------------|---------|
| Sandbox Model | 14.1 | MEDIUM | SECURITY.md | Security at a Glance (new) |
| Known Limitations | 14.2 | MEDIUM | SECURITY.md | Section 3.3 (enhanced) |

### Scenario Group 15-21: Operations & Troubleshooting

| Scenario | ID | Priority | Target Document | Section |
|----------|----|----------|-----------------|---------|
| Progress Monitoring | 15.1 | LOW | REFERENCE.md | progress command |
| Session Cleanup | 16.1 | LOW | REFERENCE.md | clean command |
| Uninstallation | 17.1 | MEDIUM | TROUBLESHOOTING.md | How to Uninstall |
| CI/CD Integration | 18.1 | LOW | (defer -- not practical yet) | -- |
| CLI Shortcuts | 19.1 | MEDIUM | REFERENCE.md + SKILL.md | CLI Shortcuts |
| Cancellation | 20.1 | HIGH | TROUBLESHOOTING.md | How to Cancel |
| Windows Issues | 21.1 | MEDIUM | TROUBLESHOOTING.md | Platform-Specific |
| Permission/Path Issues | 21.2 | MEDIUM | TROUBLESHOOTING.md + ERROR-CODES.md | Platform-Specific + DS-301/302 |

---

## 6. Priority Order for Implementation

### Priority 1 (HIGH -- unblocks new users)

Execute in this order, as later items depend on earlier ones:

| # | Task | Type | Est. Lines | Depends On |
|---|------|------|-----------|------------|
| 1 | Create GETTING-STARTED.md | New file | 250 | -- |
| 2 | Create ERROR-CODES.md | New file | 250 | -- |
| 3 | Create TROUBLESHOOTING.md | New file | 350 | ERROR-CODES.md (for cross-links) |
| 4 | Update README.md | Edit | +30 net | GETTING-STARTED.md (for links) |
| 5 | Update SKILL.md | Edit | +20 net | TROUBLESHOOTING.md, ERROR-CODES.md (for links) |

Tasks 1 and 2 can be done in parallel. Task 3 depends on 2. Tasks 4 and 5 depend on 1 and 3.

### Priority 2 (MEDIUM -- improves daily use)

| # | Task | Type | Est. Lines | Depends On |
|---|------|------|-----------|------------|
| 6 | Create REFERENCE.md | New file | 350 | -- |
| 7 | Update SECURITY.md | Edit | +20 net | REFERENCE.md (for cross-links) |
| 8 | Update ARCHITECTURE.md | Edit | +5 net | REFERENCE.md, ERROR-CODES.md |

Task 6 can start immediately. Tasks 7 and 8 depend on 6.

### Priority 3 (LOW -- polish)

| # | Task | Type |
|---|------|------|
| 9 | Add CI/CD notes to USE_CASES.md (if practical) | Edit |
| 10 | Add output format documentation to REFERENCE.md | Edit |

---

## 7. Cross-Reference Map

Every document should link to related documents. This is the planned cross-reference network:

```
README.md
  -> GETTING-STARTED.md ("Complete walkthrough")
  -> SKILL.md ("Command reference")
  -> ARCHITECTURE.md ("System design")
  -> SECURITY.md ("Security model")
  -> TROUBLESHOOTING.md ("Error recovery")
  -> USE_CASES.md ("Advanced scenarios")

GETTING-STARTED.md
  -> TROUBLESHOOTING.md ("If something goes wrong")
  -> REFERENCE.md ("Full command reference")
  -> USE_CASES.md ("Advanced use cases")

SKILL.md
  -> GETTING-STARTED.md ("New? Start here")
  -> TROUBLESHOOTING.md (replaces inline troubleshooting table)
  -> ERROR-CODES.md ("Error code reference")
  -> REFERENCE.md ("Full reference")

TROUBLESHOOTING.md
  -> ERROR-CODES.md (per-error links)
  -> REFERENCE.md ("REPL sandbox rules")
  -> GETTING-STARTED.md ("Start from scratch")

ERROR-CODES.md
  -> TROUBLESHOOTING.md ("Common fixes")
  -> REFERENCE.md ("Command reference")

REFERENCE.md
  -> GETTING-STARTED.md ("Tutorial")
  -> SECURITY.md ("Security architecture")
  -> ERROR-CODES.md ("Error codes")

SECURITY.md
  -> REFERENCE.md ("REPL sandbox user reference")
  -> ARCHITECTURE.md ("System design")

ARCHITECTURE.md
  -> REFERENCE.md ("Command reference")
  -> ERROR-CODES.md ("Error codes")
  -> SECURITY.md ("Security model")
```

---

## 8. Content Rules for the Doc Writer

### Do
- Show expected output for every command example
- Use the `[DS-NNN]` format when referencing error codes -- it's searchable
- Cross-link explicitly: `See [Error Codes](ERROR-CODES.md#ds-306)` not "see the error docs"
- Use tables for lookup data, prose for narratives
- Keep SKILL.md under 500 lines (Claude Code plugin convention)
- Write in second person active voice: "Run the scan" not "The scan should be run"

### SKILL.md vs REFERENCE.md Boundary
SKILL.md contains the *quick* reference (what Claude Code loads into context). REFERENCE.md contains the *complete* reference (every flag, every setting, every edge case). When content exists in both, SKILL.md should summarize and link to REFERENCE.md for details. Never duplicate tables between them.

### Don't
- Don't duplicate content -- link instead
- Don't mix Diataxis types in one document (e.g., no tutorial content in REFERENCE.md)
- Don't document code internals in user docs (that's for ARCHITECTURE.md or code comments)
- Don't add error handling/recovery steps to GETTING-STARTED.md (link to TROUBLESHOOTING.md)
- Don't use "see above" or "see below" -- always use explicit links
- Don't describe MAP as producing "real results" in CLI mode -- it produces placeholders

### Style
- Blockquote callouts: `> **Note:**`, `> **Warning:**`, `> **Security:**`
- Code blocks: use ` ```bash ` for commands, ` ```python ` for code, ` ```json ` for output
- Headers: `##` for major sections, `###` for subsections, never skip levels
- One blank line between sections, no trailing whitespace

---

## 9. Validation Checklist

After all changes, verify:

### Coverage (all 32 scenarios)
- [ ] Every HIGH-priority scenario has content in at least one document
- [ ] Every MEDIUM-priority scenario has content or a deliberate deferral note
- [ ] Every LOW-priority scenario is either covered or deferred with rationale

### Navigation
- [ ] A user landing on README.md can reach any other document in 1 click
- [ ] GETTING-STARTED.md links to "what's next" documents
- [ ] Every error mentioned in TROUBLESHOOTING.md links to ERROR-CODES.md
- [ ] SKILL.md troubleshooting section links to TROUBLESHOOTING.md

### Diataxis Compliance
- [ ] GETTING-STARTED.md is pure Tutorial (no reference tables, no deep explanation)
- [ ] TROUBLESHOOTING.md is pure How-To (no tutorial hand-holding, no system internals)
- [ ] ERROR-CODES.md is pure Reference (no narrative, just facts)
- [ ] REFERENCE.md is pure Reference (no tutorial, no explanation)
- [ ] SECURITY.md is Explanation with a Reference summary (acceptable blend for security docs)

### Technical Accuracy
- [ ] All error codes match error_codes.py (25 codes: DS-001 through DS-505)
- [ ] All CLI commands match deepscan_engine.py
- [ ] All configuration defaults match constants.py
- [ ] REPL allowed/blocked lists match deepscan_engine.py forbidden patterns + AST whitelist + constants.py SAFE_BUILTINS
- [ ] File paths match actual directory structure

### Length Constraints
- [ ] SKILL.md < 500 lines
- [ ] GETTING-STARTED.md: 200-300 lines
- [ ] TROUBLESHOOTING.md: 300-400 lines
- [ ] ERROR-CODES.md: 200-300 lines
- [ ] REFERENCE.md: 300-400 lines
