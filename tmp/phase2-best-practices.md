# Phase 2: Documentation Best Practices Research

> Generated: 2026-02-16
> Input: Phase 1 scenario analysis (32 scenarios, 3 personas, coverage gaps)
> Sources: Diataxis framework, Rust/TypeScript-ESLint/webpack/pytest documentation patterns, Claude Code plugin conventions

---

## 1. Framework Recommendation: Diataxis

**Recommendation: Adopt Diataxis as the organizing principle for all documentation.**

The Diataxis framework (https://diataxis.fr/) organizes documentation into four types based on a 2x2 grid of user needs:

| | Study (learning) | Work (doing) |
|---|---|---|
| **Practical** (action) | **Tutorial** -- learning-oriented, step-by-step | **How-To Guide** -- task-oriented, goal-focused |
| **Theoretical** (cognition) | **Explanation** -- understanding-oriented, context | **Reference** -- information-oriented, facts |

### Why Diataxis fits DeepScan

1. **The scenario analysis reveals the exact gap Diataxis solves.** Current docs are organized by *system component* (ARCHITECTURE.md, SECURITY.md, SKILL.md) rather than by *user need*. This is why beginners can't find end-to-end walkthroughs (Tutorial gap) and experienced users can't find task recipes (How-To gap).

2. **Diataxis is the de facto standard for Python-ecosystem tools.** Python's own documentation is adopting it. pytest, Django, and Canonical/Ubuntu use it. Since DeepScan is a Python-based plugin, users expect this pattern.

3. **It maps cleanly to the three personas identified in Phase 1:**
   - P1 (Beginner): Tutorials
   - P2 (Experienced): How-To Guides + Reference
   - P3 (Security-Conscious): Explanation + Reference

4. **The existing docs already partially fit.** SKILL.md is Reference. ARCHITECTURE.md is Explanation. USE_CASES.md mixes How-To and Explanation. The work is reorganization and gap-filling, not starting from scratch.

### How to apply incrementally

Following Diataxis's own advice: don't reorganize everything at once. Instead:
1. Tag each existing document with its Diataxis type
2. Fill the highest-priority gap first (Tutorial: Getting Started)
3. Extract mixed content into the correct type over time
4. Keep boundaries crisp -- never mix Tutorial and Reference in one document

---

## 2. Structural Recommendations

### 2.1 Proposed File Organization

Based on Claude Code plugin conventions, Diataxis, and the scenario analysis:

```
deepscan/
  README.md                          # Gateway (discovery + installation + links)
  CLAUDE.md                          # Developer/contributor guidance (keep as-is)
  TEST-PLAN.md                       # Test planning (keep as-is)
  .claude-plugin/
    plugin.json                      # Plugin manifest
  .claude/skills/deepscan/
    SKILL.md                         # Skill trigger + REFERENCE (command/config/API)
    docs/
      GETTING-STARTED.md             # TUTORIAL -- end-to-end first scan
      HOW-TO.md                      # HOW-TO -- task-oriented recipes
      ARCHITECTURE.md                # EXPLANATION -- system design (exists)
      SECURITY.md                    # EXPLANATION -- threat model (exists)
      ERROR-REFERENCE.md             # REFERENCE -- all error codes + troubleshooting
      USE_CASES.md                   # HOW-TO (exists, keep for advanced recipes)
      ADR-001-repl-security-relaxation.md  # EXPLANATION (exists)
```

### 2.2 Rationale for each file

| File | Diataxis Type | Primary Persona | Justification |
|------|---------------|-----------------|---------------|
| README.md | Gateway (none) | All | First contact. Must answer: what, why, install, next steps |
| GETTING-STARTED.md | Tutorial | P1 | Fills the #1 gap from scenario analysis: no end-to-end walkthrough |
| HOW-TO.md | How-To | P2 | Task recipes: "How to resume a scan", "How to scan incrementally" |
| SKILL.md | Reference | P2 | Already serves as command reference. Strengthen this role |
| ERROR-REFERENCE.md | Reference | P1, P2 | Fills the error code documentation gap. Extract from error_codes.py |
| ARCHITECTURE.md | Explanation | P2, P3 | Already good. Add cross-links |
| SECURITY.md | Explanation | P3 | Already thorough. Add user-friendly summary section |
| USE_CASES.md | How-To | P2 | Already good for advanced users. Cross-link from HOW-TO.md |

### 2.3 What NOT to create

- Do NOT create a separate FAQ. Integrate Q&A into How-To and Error Reference.
- Do NOT create per-module API docs. The plugin is invoked via commands, not imported.
- Do NOT create a CHANGELOG yet. Wait until there are releases to document.
- Do NOT split How-To into many small files. One file with clear headings is scannable.

### 2.4 Claude Code plugin conventions to follow

Based on the official plugin documentation (https://code.claude.com/docs/en/plugins):

- **SKILL.md must stay under 500 lines.** Move detailed content to docs/ and reference it.
- **SKILL.md frontmatter is critical.** The `description` and `triggers` fields drive skill matching. Keep them rich with semantic keywords.
- **Reference docs from SKILL.md, don't duplicate.** Use `See [Getting Started](docs/GETTING-STARTED.md)` patterns.
- **CLAUDE.md is for developers/contributors, not users.** Don't duplicate user docs there.

---

## 3. Content Recommendations

### 3.1 README.md (Gateway)

**Goal:** In 60 seconds, a reader should know: what DeepScan does, whether they need it, and how to install it.

**Structure (based on makeareadme.com and developer tool conventions):**

```markdown
# DeepScan
One-line description

## What It Does
2-3 sentences. Include a concrete before/after example.

## Quick Example
Single command + annotated output (show what a real finding looks like)

## Installation
Prerequisites, install command, verification step

## Quick Start
Link to GETTING-STARTED.md with a 3-line teaser

## Documentation
Table linking to all docs with one-line descriptions

## License
```

**Specific recommendations:**
- Add a "Quick Example" showing a real scan finding (address Scenario 4.1 gap)
- Add prerequisites: Python 3.10+, poetry, pydantic
- Add a verification step after installation: `python -c "import deepscan_engine; print('OK')"`
- Move the Testing section to a less prominent position or to CLAUDE.md (it's developer-facing)
- Remove the "No tests exist yet" warning from the prominent README position -- it's important for contributors (CLAUDE.md) but discouraging for users

### 3.2 GETTING-STARTED.md (Tutorial)

**Goal:** Take a beginner from zero to their first complete scan result in one document.

**Tutorial writing principles (from Diataxis):**
- The reader should succeed every time they follow the steps
- Show them something working, THEN explain
- Don't offer choices -- make every decision for them
- Each step should produce a visible result

**Recommended structure:**

```markdown
# Getting Started with DeepScan

## What you'll build
"By the end of this tutorial, you'll have scanned a project and
reviewed findings with file:line evidence."

## Prerequisites
- Claude Code installed and working
- A project with 10+ files to scan (or use the example below)
- Python 3.10+

## Step 1: Verify Installation
Command + expected output

## Step 2: Initialize a Scan
Command + expected output + explanation of what happened

## Step 3: Review the Scout Report
What the tree view shows + what to look for

## Step 4: Create Chunks
Command + expected output + "You now have N chunks of ~150K chars each"

## Step 5: Run the MAP Phase
CRITICAL: Explain Claude Code requirement here
Command + expected output + "Each chunk is analyzed by a sub-agent"

## Step 6: Run the REDUCE Phase
Command + expected output + what deduplication does

## Step 7: Review Your Findings
Show a real finding with confidence/evidence/location
Explain how to navigate to the source code

## Step 8: Export Results
Command + expected output file

## What's Next
Links to: How-To guides, REPL exploration, incremental scanning
```

**Critical content to include:**
- The CLI vs Claude Code distinction -- explain it at Step 5 where it matters, not before
- Expected output at every step (address the #1 gap from scenario analysis)
- Approximate scale: "This takes ~2 minutes for a 50-file project"
- What to do if something goes wrong at each step (inline, not in a separate troubleshooting page)

### 3.3 HOW-TO.md (How-To Guides)

**Goal:** Answer "How do I...?" questions from experienced users.

**How-To writing principles (from Diataxis):**
- Start with the goal, not the background
- Assume the reader knows the basics
- Be flexible -- offer alternatives where appropriate
- Don't explain WHY, link to Explanation docs for that

**Recommended recipes (ordered by scenario analysis priority):**

```markdown
# How-To Guides

## Scanning
- How to scan a specific directory or file set
- How to scan incrementally (only changed files)
- How to handle projects that exceed size limits

## Execution
- How to resume an interrupted scan
- How to cancel a running scan gracefully
- How to use the MAP phase with instructions mode
- How to use model escalation for better results

## REPL
- How to explore context with REPL helpers
- How to write custom analysis expressions
- How to understand what the REPL sandbox allows

## Results
- How to interpret findings (confidence, evidence, location)
- How to export and share results
- How to resolve contradictions in findings

## Maintenance
- How to clean up old sessions
- How to manage multiple sessions
- How to uninstall DeepScan
```

**Key principle:** Each recipe should be self-contained. A user should not need to read another document to complete the task.

### 3.4 SKILL.md (Reference)

**Goal:** Be the single source of truth for commands, flags, configuration, and behavior.

**Reference writing principles (from Diataxis):**
- Mirror the structure of the code itself
- Be austere and factual -- no persuasion, no narrative
- Keep it complete -- every command, every flag, every default
- Organize for lookup, not for reading

**Specific recommendations:**
- Keep the existing command table and configuration table (they're good)
- Add a "CLI Shortcuts" section documenting `?`, `!`, `+`, `x` (Scenario 19.1 gap)
- Add a "Modes" section clearly distinguishing full/lazy/targeted (with table)
- Add a "CLI vs Claude Code" table showing which features work where (Scenario 3.3 gap)
- Move the troubleshooting table to ERROR-REFERENCE.md and link to it
- Ensure total length stays under 500 lines per Claude Code plugin conventions

### 3.5 ERROR-REFERENCE.md (Reference -- new file)

**Goal:** Searchable reference for every error code with cause + fix.

**Pattern: Follow the Rust error index model.**

Rust's approach (https://doc.rust-lang.org/error-index.html) is the gold standard for error code documentation:
- Each error has a unique code (E0001, E0002...)
- Each entry shows: description, example that triggers it, explanation, and fix
- The entire index is searchable

**Recommended structure:**

```markdown
# DeepScan Error Reference

## Error Code Format
DeepScan errors use the format `DS-NNN` where:
- DS-0xx: Success/Info
- DS-1xx: Warnings
- DS-2xx: Validation errors
- DS-3xx: Resource errors
- DS-4xx: Processing errors
- DS-5xx: System errors

## How to Use This Reference
When you see an error like `[DS-201] ...`, search this page for DS-201.

---

## DS-201: Invalid Path
**What happened:** The path you specified doesn't exist or isn't accessible.
**Common causes:** Typo in path, relative path from wrong directory, missing permissions
**Fix:** Verify the path exists: `ls -la <path>`. Use absolute paths.

## DS-202: ...
[etc.]
```

**Content source:** Extract directly from `error_codes.py` which already has structured error definitions with remediation templates.

**Key principles (from error documentation research):**
- Every error gets its own heading (so browsers can link to `#ds-201`)
- Include "Common causes" (not just the technical cause)
- Include "Fix" with a concrete action (not "check your configuration")
- Group by category (validation, resource, processing, system)
- Include the error message text so users can search by message

### 3.6 SECURITY.md (Explanation)

**Goal:** Help security-conscious users (P3) understand the sandbox model and make informed decisions.

**Recommendations (from security documentation research):**

1. **Add a user-friendly summary at the top.** The current document is thorough but written for security experts. Add a 10-line "Security at a Glance" section:

```markdown
## Security at a Glance

DeepScan runs a sandboxed Python REPL for interactive analysis.
The sandbox enforces three layers of protection:

1. **Code filtering**: Dangerous patterns (imports, file I/O, exec) are
   blocked before execution
2. **AST validation**: Only whitelisted Python constructs are allowed
3. **Runtime limits**: 30-second timeout, memory limits, restricted builtins

What you CAN do: math, string operations, list/dict manipulation,
use built-in helpers (peek, grep, stats, etc.)

What you CANNOT do: import modules, access the filesystem, open
network connections, execute system commands

For the full threat model, see below.
```

2. **Add a "What's Allowed / What's Blocked" quick-reference table** in user-facing terms (not AST node names). Currently this info exists only in deep-technical form.

3. **Keep the detailed threat model.** It's excellent. Just make it reachable from the user-friendly summary.

4. **Move the testing checklist items to TEST-PLAN.md.** Security docs should describe the model, not track testing progress.

### 3.7 ARCHITECTURE.md (Explanation)

**Goal:** Help users understand the system design so they can use it more effectively.

**Recommendations:**
- Add a high-level diagram showing the five phases (scout, chunk, map, reduce, export)
- Add cross-links to GETTING-STARTED.md for practical demonstrations of each phase
- Keep the current technical depth -- it serves P2 and P3 well
- Add a "Key Design Decisions" section explaining WHY (map-reduce, why chunking, why sub-agents)

### 3.8 USE_CASES.md (How-To, advanced)

**Recommendations:**
- Keep as-is -- it's the strongest existing document for experienced users
- Add cross-links from HOW-TO.md for advanced versions of common tasks
- Ensure it doesn't duplicate content that moves to HOW-TO.md

---

## 4. Style and Formatting Recommendations

### 4.1 Voice and tone

| Do | Don't |
|---|---|
| Use active voice: "Run the scan" | Use passive: "The scan should be run" |
| Use second person: "You'll see..." | Use third person: "The user sees..." |
| Be direct: "This requires Claude Code" | Be hedging: "This might work better in Claude Code" |
| State facts: "MAP produces placeholders in CLI" | Apologize: "Unfortunately, MAP doesn't fully work in CLI" |

### 4.2 Command examples

Every command example should include:
1. The command itself (in a fenced code block)
2. Expected output (truncated if long, with `...` indicating omission)
3. A one-line explanation of what happened

**Example pattern:**
```markdown
Run the scout phase:
\`\`\`
/deepscan scout
\`\`\`
Output:
\`\`\`
[DS-000] Scout complete: 47 files, 12,340 lines
  src/          -- 23 files (Python)
  tests/        -- 18 files (Python)
  docs/         -- 6 files (Markdown)
\`\`\`
This builds a tree view of all files that will be analyzed.
```

### 4.3 Cross-referencing

Use consistent cross-reference patterns:
- Between docs in the same repo: `[Getting Started](docs/GETTING-STARTED.md)`
- To specific sections: `[Error Codes](docs/ERROR-REFERENCE.md#ds-201)`
- From inline text: "For configuration options, see the [command reference](SKILL.md#configuration)."

Never say "see above" or "see below" -- always link explicitly.

### 4.4 Tables vs prose

- Use **tables** for: commands, flags, configuration options, error codes, comparisons
- Use **prose** for: explanations, tutorials, how-to steps, security reasoning
- Use **code blocks** for: commands, output, file content, configuration

### 4.5 Admonitions/callouts

Use Markdown blockquotes with bold prefixes for callouts:

```markdown
> **Note:** This feature requires Claude Code environment.

> **Warning:** This will overwrite your existing session.

> **Security:** REPL commands are sandboxed but resource limits
> are not enforced on Windows.
```

Reserve these for genuinely important information. Don't use them for every note.

### 4.6 Length guidelines

| Document | Target Length | Rationale |
|----------|-------------|-----------|
| README.md | 80-120 lines | Gateway, not a manual |
| GETTING-STARTED.md | 200-300 lines | Complete but focused tutorial |
| HOW-TO.md | 300-500 lines | Many recipes, each short |
| SKILL.md | 400-500 lines | Claude Code convention: under 500 |
| ERROR-REFERENCE.md | 200-400 lines | One entry per error code |
| SECURITY.md | 300-400 lines | Keep existing depth |
| ARCHITECTURE.md | 200-300 lines | Keep existing depth |

---

## 5. Specific Recommendations by Priority

### P0: Must-do (addresses HIGH-priority scenario gaps)

| # | Action | Addresses Scenarios | New/Edit |
|---|--------|-------------------|----------|
| 1 | Create GETTING-STARTED.md with end-to-end tutorial | 3.1, 3.3, 12.1, 13.1 | New file |
| 2 | Create ERROR-REFERENCE.md extracting from error_codes.py | 6.1, 6.2, 6.4, 6.5 | New file |
| 3 | Add prerequisites + verification to README.md | 1.2, 2.2 | Edit |
| 4 | Add "CLI vs Claude Code" feature table to SKILL.md | 3.3 | Edit |
| 5 | Add user-friendly sandbox summary to SECURITY.md | 9.2 | Edit |
| 6 | Add cancellation/resume workflow to new HOW-TO.md | 8.1, 20.1 | New file |

### P1: Should-do (addresses MEDIUM-priority gaps)

| # | Action | Addresses Scenarios | New/Edit |
|---|--------|-------------------|----------|
| 7 | Add CLI shortcuts to SKILL.md | 19.1 | Edit |
| 8 | Add incremental scanning recipe to HOW-TO.md | 7.1 | In new HOW-TO.md |
| 9 | Add uninstall instructions to HOW-TO.md | 17.1 | In new HOW-TO.md |
| 10 | Add "Quick Example" with real output to README.md | 1.1, 4.1 | Edit |
| 11 | Add session overwrite protection explanation | 6.3 | In HOW-TO.md or SKILL.md |
| 12 | Add Windows compatibility notes to SKILL.md or HOW-TO.md | 21.1 | Edit |

### P2: Nice-to-do (addresses LOW-priority gaps)

| # | Action | Addresses Scenarios |
|---|--------|-------------------|
| 13 | Add export schema documentation | 4.2 |
| 14 | Add progress monitoring details | 15.1 |
| 15 | Add multi-session management guide | 8.2 |
| 16 | Document dedup/contradiction internals | 4.3 |

---

## 6. Anti-Patterns to Avoid

Based on common documentation mistakes (from Mintlify, Document360, and developer tool research):

1. **Don't write "documentation" -- write tutorials OR how-tos OR reference OR explanation.** Mixed documents are the #1 cause of documentation that doesn't help anyone.

2. **Don't duplicate content across files.** Instead, cross-link. If SKILL.md and GETTING-STARTED.md both explain chunking, one should link to the other.

3. **Don't document the code -- document the user's experience.** "The `_expand_cli_shortcuts` function maps `?` to `status`" is code docs. "Type `?` to see scan status" is user docs.

4. **Don't write for completeness -- write for findability.** A perfect document nobody can find is worse than a good document with clear headings and cross-links.

5. **Don't explain concepts in command reference.** SKILL.md should say what `--incremental` does, not why incremental scanning matters. Link to ARCHITECTURE.md for the why.

6. **Don't hide critical information.** The CLI vs Claude Code distinction is currently buried mid-document. It should be the first thing users see after installation.

---

## 7. Validation Criteria

How to verify the documentation improvements work:

### User journey test
Walk through each high-priority scenario from Phase 1 and verify:
- [ ] Can P1 complete first scan using only GETTING-STARTED.md?
- [ ] Can P2 find how to resume a scan within 30 seconds?
- [ ] Can P3 understand sandbox boundaries from SECURITY.md summary?
- [ ] Can any user look up error DS-201 and find cause + fix?

### Structural test
- [ ] Every document has exactly ONE Diataxis type
- [ ] No content is duplicated across documents
- [ ] Every command mentioned in tutorials has reference entry in SKILL.md
- [ ] Every error code in error_codes.py has entry in ERROR-REFERENCE.md

### Findability test
- [ ] README.md links to every other documentation file
- [ ] GETTING-STARTED.md links to HOW-TO.md at "What's Next"
- [ ] HOW-TO.md links to USE_CASES.md for advanced versions
- [ ] ERROR-REFERENCE.md is reachable from SKILL.md troubleshooting section

---

## 8. Research Sources

- [Diataxis Framework](https://diataxis.fr/) -- documentation organizing principle
- [Diataxis in five minutes](https://diataxis.fr/start-here/) -- practical quickstart
- [Rust Error Index](https://doc.rust-lang.org/error-index.html) -- gold standard for error code docs
- [Claude Code Plugin Docs](https://code.claude.com/docs/en/plugins) -- official plugin conventions
- [Make a README](https://www.makeareadme.com/) -- README structure conventions
- [Developer Troubleshooting Docs Best Practices](https://daily.dev/blog/developer-troubleshooting-docs-best-practices) -- troubleshooting patterns
- [I'd Rather Be Writing: Diataxis](https://idratherbewriting.com/blog/what-is-diataxis-documentation-framework) -- practical Diataxis analysis
- [typescript-eslint Troubleshooting](https://typescript-eslint.io/troubleshooting/) -- error docs example
- [webpack Getting Started](https://webpack.js.org/guides/getting-started/) -- tutorial structure example
- [Document360: Quick Start Guide](https://document360.com/blog/quick-start-guide/) -- quickstart patterns
- [Ubuntu: Diataxis adoption](https://ubuntu.com/blog/diataxis-a-new-foundation-for-canonical-documentation) -- large-scale Diataxis adoption case study
