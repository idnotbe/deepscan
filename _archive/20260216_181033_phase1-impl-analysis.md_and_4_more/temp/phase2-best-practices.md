# Phase 2: Documentation Best Practices Research

> Generated: 2026-02-16
> Sources: Anthropic official docs, Diataxis framework, community best practices, static analysis tool docs (Semgrep, SonarQube, ESLint)

---

## 1. Anthropic Official Skill Authoring Best Practices

Source: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices

### SKILL.md Structure Rules

| Rule | Current DeepScan Status |
|------|------------------------|
| `name`: max 64 chars, lowercase letters/numbers/hyphens | OK: "deepscan" |
| `description`: max 1024 chars | NEEDS CHECK: current description may be close to limit |
| SKILL.md body under 500 lines | WARNING: current SKILL.md is 210 lines -- OK but growing |
| Progressive disclosure: SKILL.md as "table of contents" pointing to detail files | GOOD: docs/ directory with ARCHITECTURE.md, SECURITY.md, USE_CASES.md |
| Scripts executed via bash, not loaded into context | GOOD: scripts/ directory |

### Key Principles from Anthropic

1. **SKILL.md is a menu, not an encyclopedia** -- route to detail files as needed
2. **Keep instructions minimal** -- Claude understands the format natively
3. **Progressive disclosure** -- load detail files on-demand, not upfront
4. **Evaluation-driven development** -- identify gaps through real use, not speculation
5. **Check activation reliability** -- ensure trigger phrases actually work

### Recommendations for DeepScan

- **Current SKILL.md is well-structured** -- it's a reference card, not a wall of text
- **Could benefit from separating the "Core Workflow" steps** into a linked guide file
- **Trigger phrases look good** -- 10 triggers covering natural language patterns
- **Progressive disclosure is already in use** -- docs/ directory is properly organized
- **Missing**: Error recovery information should be in a linked file, not just troubleshooting table

---

## 2. Diataxis Framework

Source: https://diataxis.fr/

### The Four Documentation Types

| Type | Purpose | User State | Writing Style |
|------|---------|------------|---------------|
| **Tutorial** | Learning-oriented | New, studying | "Follow these steps" -- hand-holding |
| **How-to Guide** | Task-oriented | Working, goal-directed | "To do X, do Y" -- assumes knowledge |
| **Reference** | Information-oriented | Working, needs details | "X is Y" -- complete, accurate, concise |
| **Explanation** | Understanding-oriented | Studying, curious | "The reason X works is..." -- discursive |

### Current DeepScan Documentation Mapped to Diataxis

| Document | Diataxis Type | Assessment |
|----------|---------------|------------|
| README.md | Mixed (tutorial + reference) | Could be split |
| SKILL.md | Reference | Good fit, well-structured |
| USE_CASES.md | How-to Guide | Good fit, task-oriented |
| ARCHITECTURE.md | Explanation | Good fit, describes design decisions |
| SECURITY.md | Explanation + Reference | Good fit, threat model + checklist |

### Missing Documentation Types

| Missing Type | What's Needed |
|--------------|---------------|
| **Tutorial** | End-to-end "Getting Started" walkthrough with expected output at each step |
| **How-to Guide: Error Recovery** | Task-oriented guide for each error scenario |
| **How-to Guide: Advanced Workflows** | Incremental, targeted, lazy mode step-by-step guides |
| **Reference: Error Codes** | Complete error code reference (DS-001 through DS-505) |
| **Reference: REPL Sandbox** | What's allowed/blocked in REPL, extracted from SECURITY.md |
| **Reference: Configuration** | All settings, defaults, valid ranges, and how to change them |

---

## 3. Lessons from Static Analysis Tool Documentation

### Semgrep (semgrep.dev/docs)

**What they do well:**
- "Getting Started" is literally the first page -- one command to scan
- Shows actual terminal output (what the user will see)
- Progressive complexity: `semgrep scan` -> custom rules -> CI integration
- Clear "Scan Status" section showing what happened during analysis

**Applicable to DeepScan:**
- Need a "run this one command and see results" getting started
- Show expected output at each workflow step
- Build complexity progressively (init -> exec -> map -> reduce)

### SonarQube

**What they do well:**
- Step-by-step installation with screenshots
- "Before you begin" prerequisites section
- Server setup -> project analysis -> interpreting results flow
- Dashboard/UI for results visualization

**Applicable to DeepScan:**
- Clear prerequisites section (Python version, dependencies)
- Installation verification step
- Explain the two environments (CLI vs Claude Code) before first scan

### ESLint

**What they do well:**
- Prominent "Getting Started" guide
- Configuration file format explained with examples
- Rule reference with examples of correct/incorrect code
- Migration guides between versions

**Applicable to DeepScan:**
- `.deepscanignore` should be explained like `.eslintignore`
- Error codes should be documented like ESLint rules
- Configuration reference should be standalone

---

## 4. Claude Code Plugin Community Best Practices

### From Community Analysis (secondsky/claude-skills, gists, blog posts)

1. **START_HERE.md pattern** -- some plugins create a "Start Here" file as navigation hub
2. **Plugin manifest clarity** -- plugin.json should have clear, searchable keywords
3. **Wrapper pattern for skills** -- keep SKILL.md light, move density to child files
4. **Test with real scenarios** -- 3+ real user scenarios before publishing
5. **Version documentation** -- track breaking changes between versions

### From /deep-plan Plugin (well-documented example)

- Uses SKILL.md as orchestrator, not content container
- Moves all heavy logic to Python scripts
- Clear directory structure in docs (planning/ directory)
- Resume capability documented prominently (users expect interruption)

---

## 5. Recommended Documentation Structure for DeepScan

Based on all research, here is the recommended documentation architecture:

```
README.md                          -- Overview + installation + quick start
CLAUDE.md                          -- Developer/contributor instructions
TEST-PLAN.md                       -- Test prioritization (current)

.claude/skills/deepscan/
  SKILL.md                         -- Skill interface (current, keep as-is)
  docs/
    GETTING-STARTED.md             -- NEW: Tutorial (end-to-end walkthrough)
    USE_CASES.md                   -- How-to guides (current, enhance)
    TROUBLESHOOTING.md             -- NEW: Error recovery guide
    ARCHITECTURE.md                -- Explanation (current, keep as-is)
    SECURITY.md                    -- Explanation (current, keep as-is)
    REFERENCE.md                   -- NEW: Complete command + config reference
    ERROR-CODES.md                 -- NEW: Error code reference
    ADR-001-*.md                   -- Decision records (current)
```

### Document Purposes

#### GETTING-STARTED.md (NEW - Tutorial)
- Prerequisites (Python 3.10+, poetry, pydantic)
- Installation with verification
- First scan walkthrough (init -> scout -> chunk -> map -> reduce -> export)
- Expected output at each step
- CLI vs Claude Code distinction explained upfront
- "What just happened?" explanation after each step
- Target audience: P1 (beginner developer)

#### USE_CASES.md (ENHANCE - How-to Guides)
- Already excellent -- keep current structure
- Add: Cancellation and resume workflow
- Add: Incremental scanning step-by-step
- Add: REPL custom analysis patterns
- Add: CI/CD integration notes
- Target audience: P2 (experienced developer)

#### TROUBLESHOOTING.md (NEW - How-to Guide)
- Error scenarios organized by symptom ("I see X error")
- Each entry: symptom -> cause -> fix
- Common mistakes for beginners
- Windows-specific issues
- Environment requirement failures
- Target audience: P1, P2

#### REFERENCE.md (NEW - Reference)
- Complete command reference (all subcommands with all flags)
- Configuration settings with defaults and valid ranges
- REPL sandbox: allowed/blocked operations
- CLI shortcuts (?, !, +, x)
- File locations (cache, state, chunks)
- Environment variables
- Target audience: P2

#### ERROR-CODES.md (NEW - Reference)
- All error codes DS-001 through DS-505
- Format: code, title, category, remediation
- Extracted from error_codes.py REMEDIATION_TEMPLATES
- Exit code mapping
- Target audience: P2, P3

---

## 6. Documentation Principles to Follow

### From Research

1. **Show, don't tell** -- include actual terminal output, not just commands
2. **One command to value** -- first interaction should produce visible results
3. **Fail early, explain well** -- prerequisites check should happen before first scan
4. **Progressive complexity** -- simple case first, advanced features later
5. **Task-oriented navigation** -- "I want to do X" should lead to clear instructions
6. **Error messages are documentation** -- error codes should link to docs
7. **Keep reference and tutorial separate** -- SKILL.md is reference, don't add tutorial content to it

### From Anthropic Specifically

8. **SKILL.md is a menu** -- point to detail files, don't embed everything
9. **Under 500 lines** -- split if approaching limit
10. **Test activation** -- verify trigger phrases work in practice
11. **Scripts not loaded into context** -- keep Python scripts separate (already done)
12. **Evaluate against real tasks** -- test docs against actual user scenarios from Phase 1

---

## 7. Key Anti-Patterns to Avoid

| Anti-Pattern | Why It's Bad | How to Fix |
|--------------|-------------|------------|
| Documentation organized by component | Users think in tasks, not modules | Organize by user journey |
| All info in one giant file | Overwhelming, hard to find things | Split by Diataxis type |
| Assuming user knows terminology | "MAP phase" means nothing to beginners | Define terms at first use |
| Missing prerequisites | User hits errors before first scan | Prerequisites section upfront |
| No expected output shown | User doesn't know if things are working | Show terminal output examples |
| Error messages without recovery path | User stuck when something goes wrong | Link errors to troubleshooting |
| Mixing CLI and Claude Code without warning | Most confusing aspect of DeepScan | Dedicated environment section |

---

## 8. Prioritized Documentation Changes

### Phase A: Critical (unblocks new users)
1. Add "Prerequisites" section to README.md
2. Create GETTING-STARTED.md tutorial
3. Add CLI vs Claude Code environment explanation
4. Create TROUBLESHOOTING.md with top 10 errors

### Phase B: Important (improves daily use)
5. Create REFERENCE.md with complete command/config reference
6. Create ERROR-CODES.md extracted from error_codes.py
7. Enhance USE_CASES.md with cancellation, incremental, REPL patterns
8. Add uninstallation instructions to README.md

### Phase C: Nice-to-have (polishes the experience)
9. Add expected output examples to GETTING-STARTED.md
10. Document CLI shortcuts
11. Add CI/CD integration notes
12. Add visual diagrams (workflow phases, environment diagram)
