# Phase 4: V1 Usability Report -- Fresh Developer Perspective

> **Evaluator persona**: Mid-level developer, daily Claude Code user, zero DeepScan knowledge, wants to analyze a ~500-file codebase. Not a security expert.

---

## 1. First Impressions (README Only)

**Time to understand what DeepScan does: ~30 seconds.** The opening line is clear and the "What It Does" section's 4-step numbered list (Load, Chunk, Map, Reduce) paints the picture immediately. The "When to Use" / "When NOT to Use" contrast is helpful -- I instantly know this is for big-codebase analysis, not for quick lookups.

**Positive signals:**
- Prerequisites are listed upfront (Python 3.10+, pydantic)
- Quick Example shows a realistic command
- Documentation table at the bottom gives me a roadmap

**First confusion points:**
- The installation says `claude plugin add idnotbe/deepscan` but I have no idea if this is a real command that works today or a future/aspirational one. No link to Claude Code plugin docs to validate this.
- Immediately after that, verification uses `poetry run python ...` -- but Poetry was never listed as a prerequisite. Do I need Poetry? The prerequisites say `pip install pydantic` which implies pip, not Poetry.
- The Quick Example shows `/deepscan init ./src -q "Find all security vulnerabilities"` but then says "After completing the scan workflow (init, chunk, map, reduce, export)" -- wait, doesn't `init` just start it? The parenthetical casually reveals there are 5 steps, but the example only shows one command. This feels like a bait-and-switch.
- "Testing" section says "No tests exist yet" -- on one hand, honesty is appreciated. On the other hand, for a plugin that runs sandboxed code execution, this is alarming. A new user might reconsider installing it.

**Overall first impression: 7/10.** I understand what it does and roughly how to start. But the Poetry-vs-pip confusion and the gap between the one-line Quick Example and the actual 5-step workflow create friction.

---

## 2. Journey Results

### Journey 1: Discovery to First Scan -- PASS WITH FRICTION

| Step | Status | Notes |
|------|--------|-------|
| Understand what DeepScan does | PASS | README explains it clearly |
| Find Getting Started guide | PASS | Linked prominently from README |
| Install the plugin | FRICTION | Poetry vs pip confusion (see below) |
| Run first scan (init) | PASS | GETTING-STARTED Step 2 is clear |
| Scout the context | FRICTION | `exec -c` syntax not explained (see below) |
| Create chunks | PASS | Clear instructions |
| Run MAP phase | FRICTION | CLI vs Claude Code distinction is confusing (see below) |
| Reduce and export | PASS | Straightforward |

**Friction detail -- Installation:**
- README says: `pip install pydantic` (prerequisite), then `poetry run python ...` (verification)
- GETTING-STARTED says: `pip install pydantic` (prerequisite), then `poetry run python ...` (verification)
- Neither document lists Poetry as a prerequisite. A new user who only has pip will get `command not found: poetry` on the verification step. This is a **blocking issue** for anyone who doesn't happen to have Poetry installed.
- **Suggested fix**: Either (a) add Poetry to prerequisites, or (b) use `python3 .claude/skills/deepscan/scripts/deepscan_engine.py --help` for verification (without poetry), or (c) note both options.

**Friction detail -- exec -c syntax:**
- Step 3 (Scout) shows `exec -c "print(peek_head(3000))"` but never explains what `exec -c` is. Is it a shell command? A Claude Code command? A DeepScan subcommand?
- The GETTING-STARTED guide has a "Step 2: Initialize a Scan" that shows both CLI and Claude Code forms, but Steps 3-6 only show bare commands like `exec -c "..."`, `map`, `reduce`, `export-results`. These are not prefixed with `poetry run python ... ` nor with `/deepscan`. A new user doesn't know how to invoke them.
- **Suggested fix**: Add a brief note at the top of Step 3 like: "The following commands are DeepScan subcommands. In Claude Code, use them directly (e.g., type `exec -c "..."`). In CLI mode, prefix with `poetry run python .claude/skills/deepscan/scripts/deepscan_engine.py`."

**Friction detail -- MAP in CLI vs Claude Code:**
- GETTING-STARTED Step 5 shows `map` and then immediately warns about CLI-only mode producing placeholders. But it doesn't clearly tell me: "If you're reading this in a terminal, `map` won't do real analysis." The "Environment Note" at the top of the guide covers this, but by Step 5 I've forgotten it.
- **Suggested fix**: Add a callout box at Step 5: "Running in CLI? You'll see placeholder results. Use `/deepscan map` in Claude Code for real analysis."

### Journey 2: Configuration and Advanced Usage -- PASS WITH FRICTION

| Step | Status | Notes |
|------|--------|-------|
| Find configuration options | PASS | REFERENCE.md has a clear table |
| Understand how to change settings | FRICTION | No example of WHERE to set config |
| Find use case examples | PASS | USE_CASES.md is excellent |
| Customize agent type | PASS | `--agent-type` is documented in multiple places |

**Friction detail -- WHERE to configure:**
- REFERENCE.md lists configuration settings (chunk_size, max_parallel_agents, etc.) with defaults and ranges. But it never says WHERE these settings go. Is there a config file? An environment variable? A command-line flag? Do I create a `.deepscan.json`? A `deepscan.yaml`?
- I see `--adaptive` as a flag on `init`, and `write_chunks(size=150000)` accepts size as a parameter. But what about `max_parallel_agents` or `enable_escalation`? There's no `--max-parallel-agents` flag documented on `map`.
- The Error Codes document references "configuration file" (DS-401, DS-402) but never says what format or path this file uses.
- **Suggested fix**: Add a "Configuration File" section to REFERENCE.md specifying: file name, format (JSON/YAML/TOML), location, and a complete example file.

**Positive**: USE_CASES.md is genuinely excellent. The end-to-end scenarios (Legacy System Handover, Security Incident Response, Migration Impact Analysis) are practical and clearly structured. The "DeepScan vs Simple Tools" comparison table prevents overuse.

### Journey 3: Error Recovery -- PASS

| Step | Status | Notes |
|------|--------|-------|
| DS-301 recovery | PASS | ERROR-CODES.md has clear cause and fix |
| Cancel a long scan | PASS | TROUBLESHOOTING.md explains single/double Ctrl+C |
| Resume from checkpoint | PASS | Clear `list` then `resume` workflow |

This is genuinely well done. ERROR-CODES.md is one of the best error reference documents I've seen in a plugin. Each code has: what happened, common causes, and fix. The Quick Lookup Table at the bottom is a great touch.

**One minor note**: The DS-505 entry has a note saying "The remediation template in the source code suggests `deepscan --resume {session_id}`. The correct command is `resume <session_hash>`." This honesty about a source code inconsistency is appreciated, but it also suggests the code hasn't been updated to match the docs (or vice versa). Not a user-facing problem, but a signal.

### Journey 4: Security Understanding -- PASS WITH FRICTION

| Step | Status | Notes |
|------|--------|-------|
| Find what REPL sandbox allows | PASS | REFERENCE.md has complete tables |
| Understand security model | FRICTION | SECURITY.md is thorough but technical |

**Friction detail -- SECURITY.md accessibility:**
- The document is clearly written for security engineers, not regular developers. Terms like "defense-in-depth", "ReDoS", "RLIMIT_AS", "HMAC signature", "CVE-2026-002" appear without explanation.
- The trust boundary ASCII diagram is helpful, but the 5-layer architecture diagram uses terse labels.
- For my persona (non-security-expert), what I really want to know is: "Is it safe to run this on my codebase? What can the sandbox NOT do?" -- and I can figure that out from REFERENCE.md's "Blocked Operations" table, which is much more accessible.
- **Suggested fix**: Add a "Security for Users" section at the top of SECURITY.md (or a section in REFERENCE.md) with plain-language statements like: "DeepScan's REPL cannot access your filesystem, install packages, make network calls, or execute arbitrary code. It can only use the 36 built-in Python functions and the DeepScan helper functions."

---

## 3. Top 10 Confusion Points (Prioritized)

### Severity Legend
- **BLOCKING**: New user cannot proceed without external help
- **HIGH**: Significant confusion requiring re-reading or guessing
- **MEDIUM**: Friction that slows down but doesn't stop the user
- **LOW**: Cosmetic or minor clarity issue

| # | Severity | Location | Issue | Suggested Fix |
|---|----------|----------|-------|---------------|
| 1 | **BLOCKING** | README + GETTING-STARTED | `poetry run python ...` used for verification but Poetry is not listed as a prerequisite. Users with only pip will fail. | Add Poetry to prerequisites OR provide a non-Poetry verification command like `python3 .claude/skills/deepscan/scripts/deepscan_engine.py --help` |
| 2 | **HIGH** | REFERENCE.md | Configuration settings table lists 13 settings (chunk_size, max_parallel_agents, etc.) but never explains WHERE to put them. No config file format, path, or example. DS-401/DS-402 errors reference "config file" without specifying it. | Add a "Configuration File" section with path, format, and example |
| 3 | **HIGH** | GETTING-STARTED Steps 3-7 | Commands like `exec -c "..."`, `map`, `reduce`, `export-results` appear without explaining how to invoke them. Are they shell commands? Claude Code commands? DeepScan CLI subcommands? | Add a "How to Run Commands" callout explaining both CLI and Claude Code invocation |
| 4 | **HIGH** | GETTING-STARTED "What's Next" | Links use bare filenames: `[Troubleshooting](TROUBLESHOOTING.md)`. Since GETTING-STARTED.md is in `.claude/skills/deepscan/docs/`, these resolve correctly on GitHub. But README.md uses full relative paths. This inconsistency might confuse contributors editing docs. | Consistent linking convention (all relative from doc location) -- this actually works, just noting the difference |
| 5 | **MEDIUM** | README Quick Example | `/deepscan init ./src -q "Find all security vulnerabilities"` implies a one-command experience, but the actual workflow is 5 steps (init, chunk, map, reduce, export). The gap between the promise and reality is jarring. | Either show the full quick workflow or add a note: "This initializes the scan. See Getting Started for the full 5-step workflow." |
| 6 | **MEDIUM** | GETTING-STARTED "Environment Note" | The CLI vs Claude Code distinction is critical but presented as a table early on, then forgotten by Step 5 (MAP). A user in CLI mode will get confused by placeholder results. | Add inline reminders at Steps 5 and 6 about the CLI limitation |
| 7 | **MEDIUM** | TROUBLESHOOTING | The "Forbidden pattern detected" section mentions "CVE-2026-002" for the `re` module removal. This is alarming without context. Is this a real CVE? (It's dated in the future.) A non-security-expert user sees "CVE" and panics. | Either explain it briefly or remove the CVE reference from user-facing docs |
| 8 | **MEDIUM** | ERROR-CODES.md line 5 | "The `doc_url` property in error messages generates URLs like `https://deepscan.io/docs/errors/DS-NNN`. These URLs do not currently resolve." -- Honest, but a new user seeing these URLs in error output will try to click them and get 404s. | Consider removing the `doc_url` from error output until the URLs work, or point them to the local ERROR-CODES.md file |
| 9 | **LOW** | SECURITY.md Section 6.2 | "HMAC Signature (Not Yet Implemented)" is documented with code samples. This looks like a feature that exists but it's explicitly marked as not implemented. Slightly confusing -- why document unimplemented features? | Move to a "Future Work" section or remove until implemented |
| 10 | **LOW** | SKILL.md vs README.md | The SKILL.md and README.md have overlapping but slightly different information. SKILL.md is more concise but has the same command reference. A user might read both and wonder which is authoritative. | Add a note at the top of SKILL.md: "This is the quick reference. For full documentation, see the docs/ directory." |

---

## 4. What's Great (Positive Feedback)

1. **ERROR-CODES.md is outstanding.** Every error code has a clear structure: what happened, common causes, and fix. The Quick Lookup Table at the bottom is excellent for scanning. The categorization by code range (0xx=validation, 1xx=parsing, etc.) is intuitive. This is best-in-class error documentation.

2. **TROUBLESHOOTING.md covers real workflows.** The "How-To" sections (cancel a scan, resume, scan incrementally, exclude files, MAP instructions mode, uninstall) answer the exact questions a user would ask. The cancel/resume flow with single vs double Ctrl+C is particularly well-explained.

3. **USE_CASES.md provides genuine value.** The end-to-end scenarios are not contrived -- Legacy System Handover, Security Incident Response, and Migration Impact Analysis are real problems. The "DeepScan vs Simple Tools" table prevents tool overuse.

4. **The "When NOT to Use" section in README.md** is rare and valuable. Most tools only tell you when to use them. Telling me to use Grep, Glob, or Read for simpler tasks shows honesty and good UX design.

5. **REFERENCE.md is comprehensive.** The REPL Sandbox section with Safe Builtins, Allowed Syntax, Blocked Operations, and Forbidden Patterns gives a complete picture. The Helper Functions tables with signatures and return types are useful.

6. **Cross-referencing between documents is thorough.** Every major document has a "See Also" section pointing to related documents. ERROR-CODES entries link to TROUBLESHOOTING, and vice versa.

7. **The GETTING-STARTED guide has "Expected output" blocks.** Showing what the user should see after each command reduces anxiety and helps verify they're on the right track.

8. **Size limits are comprehensively documented.** REFERENCE.md's Size Limits table covers everything from single-file limits to session cache totals. This prevents surprises.

---

## 5. Overall Usability Score

### Score: 7.5 / 10

### Justification

**What earns points:**
- Clear problem statement and value proposition (README)
- Comprehensive error reference (ERROR-CODES.md) -- genuinely best-in-class
- Practical troubleshooting with real workflows (TROUBLESHOOTING.md)
- Honest about limitations (no tests, CLI vs Claude Code, unresolved URLs)
- Thorough cross-referencing between documents
- Realistic use cases with end-to-end examples

**What costs points:**
- **Poetry prerequisite gap (-1.0)**: This is a blocking issue. A user following the docs exactly will hit `command not found` on verification.
- **Missing configuration file documentation (-0.5)**: Settings are listed but there's no explanation of where to put them.
- **Command invocation ambiguity (-0.5)**: Steps 3-7 in GETTING-STARTED don't explain how commands are actually run.
- **Quick Example overpromise (-0.25)**: The one-liner suggests simplicity that doesn't match the 5-step reality.
- **CVE reference without context (-0.25)**: Alarming for non-security-experts.

**Bottom line:** A mid-level developer can successfully use DeepScan by reading these docs, but they'll hit 1-2 moments of confusion that require guessing or external research. Fixing the Poetry prerequisite issue and adding a configuration file section would push this to 8.5+.

---

## Appendix: Link Validation

| Source File | Link Target | Valid? |
|-------------|-------------|--------|
| README.md -> GETTING-STARTED.md | `.claude/skills/deepscan/docs/GETTING-STARTED.md` | YES |
| README.md -> SKILL.md | `.claude/skills/deepscan/SKILL.md` | YES |
| README.md -> REFERENCE.md | `.claude/skills/deepscan/docs/REFERENCE.md` | YES |
| README.md -> ERROR-CODES.md | `.claude/skills/deepscan/docs/ERROR-CODES.md` | YES |
| README.md -> TROUBLESHOOTING.md | `.claude/skills/deepscan/docs/TROUBLESHOOTING.md` | YES |
| README.md -> ARCHITECTURE.md | `.claude/skills/deepscan/docs/ARCHITECTURE.md` | YES |
| README.md -> SECURITY.md | `.claude/skills/deepscan/docs/SECURITY.md` | YES |
| README.md -> USE_CASES.md | `.claude/skills/deepscan/docs/USE_CASES.md` | YES |
| README.md -> TEST-PLAN.md | `TEST-PLAN.md` | YES |
| README.md -> LICENSE | `LICENSE` | YES |
| GETTING-STARTED.md -> TROUBLESHOOTING.md | `TROUBLESHOOTING.md` | YES (same dir) |
| GETTING-STARTED.md -> USE_CASES.md | `USE_CASES.md` | YES (same dir) |
| GETTING-STARTED.md -> REFERENCE.md | `REFERENCE.md` | YES (same dir) |
| GETTING-STARTED.md -> ERROR-CODES.md | `ERROR-CODES.md` | YES (same dir) |
| SECURITY.md -> ADR-001 | `ADR-001-repl-security-relaxation.md` | YES (same dir) |
| ERROR-CODES.md -> TROUBLESHOOTING.md | `TROUBLESHOOTING.md` | YES (same dir) |
| ERROR-CODES.md -> REFERENCE.md | `REFERENCE.md` | YES (same dir) |
| SKILL.md -> docs/* | `docs/TROUBLESHOOTING.md`, etc. | YES (relative from SKILL.md dir) |

All cross-document links resolve correctly. No broken links found.
