# Phase 1: User Scenario Analysis for DeepScan Plugin

> Generated: 2026-02-16
> Source: Full codebase analysis of 17 Python modules, SKILL.md, README.md, ARCHITECTURE.md, SECURITY.md, USE_CASES.md, plugin.json

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Total scenarios identified | 32 |
| High priority | 14 |
| Medium priority | 12 |
| Low priority | 6 |
| Current doc coverage: Good | 8 |
| Current doc coverage: Partial | 15 |
| Current doc coverage: Missing | 9 |

---

## Persona Definitions

### P1: Beginner Developer
- New to Claude Code plugins
- May not understand map-reduce concepts
- Needs step-by-step guidance with copy-paste commands
- Likely confused by CLI vs Claude Code environment distinction

### P2: Experienced Developer
- Familiar with Claude Code, plugins, and CLI tools
- Wants efficient workflows, configuration reference
- Needs advanced features (incremental, adaptive, targeted)

### P3: Security-Conscious Developer
- Wants to understand sandbox boundaries before using REPL
- Needs threat model, known limitations, and escape vector documentation
- May be evaluating plugin for enterprise use

---

## Scenario 1: Discovery & Installation

### 1.1 Finding the Plugin
- **User's Goal**: Discover DeepScan exists and understand if it fits their needs
- **Current Doc Support**: PARTIAL
- **Key Gaps**:
  - README.md has good "What It Does" / "When to Use" / "When NOT to Use" sections
  - Missing: comparison with alternatives (e.g., plain grep, other analysis tools)
  - Missing: visual examples of output (what does a scan result look like?)
  - Missing: "before/after" showing the problem DeepScan solves
- **Priority**: HIGH
- **Personas**: P1, P2

### 1.2 Installing the Plugin
- **User's Goal**: Get DeepScan working in their Claude Code environment
- **Current Doc Support**: PARTIAL
- **Key Gaps**:
  - README.md shows `claude plugin add idnotbe/deepscan` and `git clone` but no verification step
  - Missing: Prerequisites (Python version, poetry, pydantic dependency)
  - Missing: "Verify installation worked" command
  - Missing: What happens if installation fails (common errors)
  - plugin.json references `.claude/skills/deepscan` -- user needs to understand this path structure
- **Priority**: HIGH
- **Personas**: P1, P2

### 1.3 Understanding Plugin vs Skill Architecture
- **User's Goal**: Understand relationship between plugin.json, SKILL.md, and scripts/
- **Current Doc Support**: MISSING
- **Key Gaps**:
  - No documentation explains the Claude Code plugin/skill architecture from user perspective
  - Users don't know that SKILL.md triggers are what activate the plugin
  - No explanation of where files live and why
- **Priority**: MEDIUM
- **Personas**: P1

---

## Scenario 2: First-Time Setup & Configuration

### 2.1 Pre-Scan Configuration
- **User's Goal**: Configure DeepScan before running first scan
- **Current Doc Support**: PARTIAL
- **Key Gaps**:
  - SKILL.md has a "Configuration" table with defaults
  - Missing: How to actually SET these values (no config file documented, only CLI flags)
  - Missing: `.deepscanignore` is documented in USE_CASES.md but not in README or getting-started
  - Missing: Guidance on which settings to change for common use cases
- **Priority**: MEDIUM
- **Personas**: P2

### 2.2 Understanding the Environment Requirements
- **User's Goal**: Know if DeepScan will work in their environment
- **Current Doc Support**: MISSING
- **Key Gaps**:
  - CLI mode vs Claude Code mode distinction is buried deep in SKILL.md
  - The critical fact that "MAP phase only works in Claude Code" is only explained mid-workflow
  - Windows users need PYTHONIOENCODING=utf-8 but this is only in troubleshooting table
  - No explicit Python version requirements documented (code uses 3.10+ features like `X | None`)
  - Poetry dependency not documented in README
- **Priority**: HIGH
- **Personas**: P1, P2

---

## Scenario 3: Running First Scan (Happy Path)

### 3.1 Quick Start - Small Project
- **User's Goal**: Run DeepScan on a small project to see what it does
- **Current Doc Support**: PARTIAL
- **Key Gaps**:
  - README shows `/deepscan init ./src -q "Find all security vulnerabilities"` -- good
  - Missing: Complete end-to-end example showing init -> scout -> chunk -> map -> reduce -> export
  - Missing: Expected output at each step
  - Missing: Approximate time expectations
  - The workflow in SKILL.md assumes user knows what "scout", "chunk", "map", "reduce" mean
- **Priority**: HIGH
- **Personas**: P1

### 3.2 Quick Start via Natural Language Triggers
- **User's Goal**: Trigger DeepScan through natural conversation with Claude Code
- **Current Doc Support**: PARTIAL
- **Key Gaps**:
  - SKILL.md lists trigger phrases ("analyze large codebase", "security audit across", etc.)
  - Missing: Example of how this looks in practice (user types phrase, what happens?)
  - Missing: Which triggers map to which mode
  - Users may not realize these triggers exist
- **Priority**: MEDIUM
- **Personas**: P1

### 3.3 Understanding the CLI vs Claude Code Split
- **User's Goal**: Know which commands work in CLI and which need Claude Code
- **Current Doc Support**: PARTIAL
- **Key Gaps**:
  - SKILL.md has a note: "Full sub-agent processing requires Claude Code environment"
  - `cmd_map()` prints a large warning about CLI-only mode producing placeholders
  - Missing: Clear upfront table showing which features require which environment
  - Missing: Explanation of what "placeholder results" means and why they exist
  - This is the #1 source of confusion for new users
- **Priority**: HIGH
- **Personas**: P1, P2

---

## Scenario 4: Understanding Results

### 4.1 Interpreting Scan Output
- **User's Goal**: Understand what the findings mean and how to act on them
- **Current Doc Support**: PARTIAL
- **Key Gaps**:
  - ARCHITECTURE.md shows `Finding` model (point, evidence, confidence, location)
  - Missing: Example of actual output (what does a real finding look like?)
  - Missing: Guide to confidence levels (what does "high" vs "medium" vs "low" mean?)
  - Missing: How to navigate from finding to source code (file:line references)
- **Priority**: HIGH
- **Personas**: P1, P2

### 4.2 Exporting and Sharing Results
- **User's Goal**: Get results in a format they can share with team
- **Current Doc Support**: PARTIAL
- **Key Gaps**:
  - `export-results output.json` is documented in SKILL.md
  - Missing: Schema/structure of the exported JSON
  - Missing: Examples of post-processing exported results
  - Missing: How to generate human-readable reports from JSON export
- **Priority**: MEDIUM
- **Personas**: P2

### 4.3 Understanding Deduplication and Contradiction Detection
- **User's Goal**: Trust that results are accurate and not duplicated
- **Current Doc Support**: PARTIAL
- **Key Gaps**:
  - ARCHITECTURE.md mentions "Jaccard similarity (threshold: 0.7)" and "Contradiction detection"
  - Missing: What happens when contradictions are found? How to resolve them?
  - Missing: How to tune similarity threshold
- **Priority**: LOW
- **Personas**: P2

---

## Scenario 5: Configuration Tuning

### 5.1 Chunk Size Optimization
- **User's Goal**: Optimize chunk size for their specific codebase
- **Current Doc Support**: GOOD
- **Key Gaps**:
  - SKILL.md documents chunk_size range (50K-300K) and defaults
  - constants.py has CHUNK_SIZE_BY_EXTENSION mapping
  - USE_CASES.md has chunking strategy table
  - Minor gap: No guidance on when to increase vs decrease overlap
- **Priority**: LOW
- **Personas**: P2

### 5.2 Agent Type Selection
- **User's Goal**: Choose the right specialized agent for their analysis
- **Current Doc Support**: GOOD
- **Key Gaps**:
  - SKILL.md, README.md, USE_CASES.md all document the 4 agent types
  - `--agent-type` flag is documented with choices
  - Minor gap: No examples of output differences between agent types
- **Priority**: MEDIUM
- **Personas**: P2

### 5.3 Custom Ignore Patterns (.deepscanignore)
- **User's Goal**: Exclude irrelevant files from analysis
- **Current Doc Support**: GOOD
- **Key Gaps**:
  - USE_CASES.md section 10 has clear documentation with example file
  - state_manager.py docstring explains the feature
  - Minor gap: Not mentioned in README.md or getting-started flow
- **Priority**: LOW
- **Personas**: P2

---

## Scenario 6: Error Recovery

### 6.1 "No State Found" Error
- **User's Goal**: Understand why they got an error and fix it
- **Current Doc Support**: PARTIAL
- **Key Gaps**:
  - SKILL.md troubleshooting table lists this error
  - error_codes.py has DS_306_SESSION_NOT_FOUND with remediation
  - Missing: Full list of error codes with remediation in user-facing docs
  - Missing: The error code system (DS-NNN) is not documented for users
- **Priority**: HIGH
- **Personas**: P1

### 6.2 "Forbidden Pattern" Error
- **User's Goal**: Understand what they typed wrong in the REPL
- **Current Doc Support**: PARTIAL
- **Key Gaps**:
  - SKILL.md troubleshooting says "Use allowed helpers, not `__import__`"
  - Missing: Complete list of what IS allowed vs what IS NOT in the REPL
  - Missing: Common mistakes and their fixes
  - Missing: The distinction between "forbidden pattern" and "forbidden AST node" errors
- **Priority**: HIGH
- **Personas**: P1, P2

### 6.3 Session Overwrite Protection
- **User's Goal**: Understand why `init` is refusing to run
- **Current Doc Support**: MISSING
- **Key Gaps**:
  - cmd_init() has overwrite protection (warns about existing session, suggests --force)
  - This is not documented anywhere in user-facing docs
  - Missing: How to handle the "Active session already exists" warning
- **Priority**: MEDIUM
- **Personas**: P1

### 6.4 Timeout Errors
- **User's Goal**: Fix "Execution timed out" errors
- **Current Doc Support**: PARTIAL
- **Key Gaps**:
  - SKILL.md troubleshooting doesn't mention timeout errors
  - The `--timeout` flag on `exec` is documented in CLI help but not in user docs
  - Missing: Dynamic timeout calculation for write_chunks is not explained to users
  - Missing: Guidance on what timeout values to use
- **Priority**: MEDIUM
- **Personas**: P2

### 6.5 File Too Large / Context Too Large Errors
- **User's Goal**: Scan a project that exceeds size limits
- **Current Doc Support**: PARTIAL
- **Key Gaps**:
  - SKILL.md troubleshooting mentions "Files >10MB skipped"
  - Missing: How to handle the 50MB total context limit
  - Missing: Strategies for large codebases (use --lazy, --target, or split analysis)
- **Priority**: MEDIUM
- **Personas**: P2

---

## Scenario 7: Incremental Scanning

### 7.1 Setting Up Incremental Analysis
- **User's Goal**: Only re-analyze changed files on subsequent runs
- **Current Doc Support**: PARTIAL
- **Key Gaps**:
  - SKILL.md mentions `--incremental --previous-session <hash>` flags
  - USE_CASES.md section 8 has a brief table
  - Missing: Step-by-step workflow for setting up incremental scanning
  - Missing: How to find the previous session hash
  - Missing: Expected speedup (mentioned as 3-10x but no concrete guidance)
- **Priority**: MEDIUM
- **Personas**: P2

### 7.2 Understanding Delta Detection
- **User's Goal**: Verify which files will be re-analyzed
- **Current Doc Support**: MISSING
- **Key Gaps**:
  - incremental.py has FileDelta with changed/added/deleted files
  - cmd_init() prints incremental stats, but only briefly
  - Missing: How to preview what delta detection found before running analysis
  - Missing: How hash algorithms work (xxHash vs SHA-256)
- **Priority**: LOW
- **Personas**: P2

---

## Scenario 8: Checkpoint/Resume

### 8.1 Resuming an Interrupted Scan
- **User's Goal**: Continue a scan that was interrupted (network issue, Ctrl+C, crash)
- **Current Doc Support**: PARTIAL
- **Key Gaps**:
  - SKILL.md shows `resume [hash]` command
  - USE_CASES.md section 6 mentions resume scenario
  - Missing: What happens to in-progress chunks when interrupted?
  - Missing: How to verify checkpoint integrity
  - Missing: How cancellation (Ctrl+C) differs from crash recovery
- **Priority**: HIGH
- **Personas**: P1, P2

### 8.2 Managing Multiple Sessions
- **User's Goal**: Work on multiple projects simultaneously
- **Current Doc Support**: PARTIAL
- **Key Gaps**:
  - `list` command shows all sessions
  - `resume` switches between sessions
  - Missing: Best practices for multi-session workflows
  - Missing: How disk space is consumed (cache location, GC)
- **Priority**: LOW
- **Personas**: P2

---

## Scenario 9: REPL Usage

### 9.1 Exploring Context with REPL Helpers
- **User's Goal**: Use peek, grep, and other helpers to explore loaded context
- **Current Doc Support**: GOOD
- **Key Gaps**:
  - SKILL.md has comprehensive helper function table
  - USE_CASES.md has scout function examples
  - Minor gap: No interactive tutorial or "try these commands" workflow
- **Priority**: MEDIUM
- **Personas**: P1

### 9.2 Understanding REPL Sandbox Restrictions
- **User's Goal**: Know what they can and cannot do in the REPL
- **Current Doc Support**: PARTIAL
- **Key Gaps**:
  - SECURITY.md has "What's Allowed" and "What's Blocked" tables
  - Missing: This information is not in user-facing docs (only in security architecture doc)
  - Missing: Practical examples of allowed/blocked patterns for typical use cases
  - Missing: Why certain things are blocked (security reasoning is not user-accessible)
- **Priority**: HIGH
- **Personas**: P1, P3

### 9.3 Writing Custom Analysis in REPL
- **User's Goal**: Write Python expressions to analyze context beyond built-in helpers
- **Current Doc Support**: MISSING
- **Key Gaps**:
  - No documentation on writing custom analysis code
  - Users don't know which builtins are available (SAFE_BUILTINS in constants.py)
  - Missing: Examples of useful custom analysis patterns
  - Missing: How to combine helpers with custom Python code
- **Priority**: MEDIUM
- **Personas**: P2

---

## Scenario 10: Lazy Mode Workflows

### 10.1 Exploring a Large Codebase Progressively
- **User's Goal**: Start with structure overview, then drill into interesting areas
- **Current Doc Support**: GOOD
- **Key Gaps**:
  - USE_CASES.md section 1 has lazy mode examples with commands
  - SKILL.md has lazy mode helper table
  - cmd_init() outputs HATEOAS hints (next steps) when in lazy mode
  - Minor gap: How to transition from lazy mode to full/targeted mode
- **Priority**: MEDIUM
- **Personas**: P1, P2

### 10.2 Loading Specific Files in Lazy Mode
- **User's Goal**: Load and analyze specific files without loading entire codebase
- **Current Doc Support**: PARTIAL
- **Key Gaps**:
  - `load_file()` and `grep_file()` helpers are documented
  - Missing: Workflow for "I found something interesting in tree view, now what?"
  - Missing: Can you chunk and map after loading files in lazy mode?
- **Priority**: MEDIUM
- **Personas**: P2

---

## Scenario 11: Targeted Mode Workflows

### 11.1 Analyzing Specific Files/Directories
- **User's Goal**: Run deep analysis on only a subset of the codebase
- **Current Doc Support**: GOOD
- **Key Gaps**:
  - USE_CASES.md section 1 has targeted mode examples
  - `--target` flag is well documented
  - Minor gap: What happens if targets overlap? (state_manager.py deduplicates, but not documented)
- **Priority**: MEDIUM
- **Personas**: P2

---

## Scenario 12: MAP Phase - Parallel Processing

### 12.1 Running the MAP Phase in Claude Code
- **User's Goal**: Process chunks using parallel sub-agents
- **Current Doc Support**: PARTIAL
- **Key Gaps**:
  - SKILL.md shows `map [--escalate]` command
  - Missing: Step-by-step for getting real results (not placeholders)
  - Missing: How to verify sub-agents are running
  - Missing: Cost implications (haiku vs sonnet, number of API calls)
- **Priority**: HIGH
- **Personas**: P1, P2

### 12.2 Using MAP Instructions Mode
- **User's Goal**: Generate prompts for manual Task tool execution
- **Current Doc Support**: PARTIAL
- **Key Gaps**:
  - `map --instructions` is documented in SKILL.md
  - USE_CASES.md section 11 covers pagination
  - Missing: How to actually execute the generated prompts in Claude Code
  - Missing: How to feed results back (`add_result()` is shown but workflow is unclear)
- **Priority**: HIGH
- **Personas**: P2

### 12.3 Model Escalation
- **User's Goal**: Retry failed chunks with a more capable model
- **Current Doc Support**: PARTIAL
- **Key Gaps**:
  - `map --escalate` is documented
  - SKILL.md mentions "haiku -> sonnet on failures"
  - Missing: Budget limits ($5 sonnet cap, 15% chunks) are mentioned but not in user-facing docs
  - Missing: When to use escalation vs adjusting chunk size
- **Priority**: MEDIUM
- **Personas**: P2

---

## Scenario 13: REDUCE Phase - Aggregation

### 13.1 Running the REDUCE Phase
- **User's Goal**: Aggregate all chunk results into final findings
- **Current Doc Support**: PARTIAL
- **Key Gaps**:
  - `reduce` command exists but is barely documented
  - Missing: What happens during reduce (dedup, contradiction detection, ghost cleanup)
  - Missing: Expected output format
  - Missing: What to do if reduce says "all results are placeholders"
- **Priority**: HIGH
- **Personas**: P1, P2

---

## Scenario 14: Security Considerations

### 14.1 Understanding the Sandbox Model
- **User's Goal**: Trust that the REPL is safe to use on their codebase
- **Current Doc Support**: GOOD (for security audience)
- **Key Gaps**:
  - SECURITY.md has comprehensive threat model and defense-in-depth
  - Missing: User-friendly summary of what the sandbox prevents
  - Missing: Version of this information appropriate for non-security-experts
- **Priority**: MEDIUM
- **Personas**: P3

### 14.2 Known Limitations and Risks
- **User's Goal**: Make informed decision about using DeepScan on sensitive code
- **Current Doc Support**: PARTIAL
- **Key Gaps**:
  - SECURITY.md mentions zombie thread DoS and memory DoS limitations
  - CLAUDE.md mentions known gaps (introspection primitives, no Windows testing)
  - Missing: Single consolidated "Known Limitations" section in user docs
  - Missing: Mitigation guidance (Docker, resource limits)
- **Priority**: MEDIUM
- **Personas**: P3

---

## Scenario 15: Progress Monitoring

### 15.1 Watching a Long-Running Scan
- **User's Goal**: Monitor progress of a large analysis in real-time
- **Current Doc Support**: PARTIAL
- **Key Gaps**:
  - `progress` and `progress --watch` commands exist
  - SKILL.md mentions `tail -f ~/.claude/cache/deepscan/{hash}/progress.jsonl`
  - Missing: What information is in progress.jsonl entries
  - Missing: How to interpret progress percentages
- **Priority**: LOW
- **Personas**: P2

---

## Scenario 16: Session Cleanup & Maintenance

### 16.1 Cleaning Up Old Sessions
- **User's Goal**: Free disk space from old analysis sessions
- **Current Doc Support**: GOOD
- **Key Gaps**:
  - `clean --older-than 7` documented in SKILL.md and USE_CASES.md
  - `abort <hash>` documented
  - Minor gap: Where is cache stored and how much space does it use?
- **Priority**: LOW
- **Personas**: P2

---

## Scenario 17: Uninstallation

### 17.1 Removing the Plugin
- **User's Goal**: Completely remove DeepScan from their Claude Code setup
- **Current Doc Support**: MISSING
- **Key Gaps**:
  - No uninstallation instructions anywhere
  - Missing: How to remove the plugin registration
  - Missing: How to clean up cache data at `~/.claude/cache/deepscan/`
  - Missing: Whether any settings or hooks remain after removal
- **Priority**: MEDIUM
- **Personas**: P1, P2

---

## Scenario 18: CI/CD Integration

### 18.1 Automating DeepScan in Pipelines
- **User's Goal**: Run DeepScan as part of CI/CD for automated code analysis
- **Current Doc Support**: MISSING
- **Key Gaps**:
  - USE_CASES.md section 8 mentions "CI/CD pipeline" as an incremental use case
  - No actual CI/CD integration guide exists
  - Missing: How to run DeepScan non-interactively
  - Missing: Exit codes for automation (error_codes.py has them but they're not documented for users)
  - Missing: How to consume JSON output in pipelines
  - Note: This may not be practical yet since MAP requires Claude Code environment
- **Priority**: LOW
- **Personas**: P2

---

## Scenario 19: CLI Shortcuts

### 19.1 Using Shortcut Commands
- **User's Goal**: Use efficient shortcuts for common operations
- **Current Doc Support**: MISSING
- **Key Gaps**:
  - `_expand_cli_shortcuts()` in deepscan_engine.py defines: `?` -> status, `!` -> exec, `+` -> resume, `x` -> abort
  - Also: passing a path directly acts as `init <path>`
  - None of these shortcuts are documented anywhere
- **Priority**: MEDIUM
- **Personas**: P2

---

## Scenario 20: Cancellation & Graceful Shutdown

### 20.1 Cancelling a Running Scan
- **User's Goal**: Stop a scan that's taking too long or was started with wrong parameters
- **Current Doc Support**: MISSING
- **Key Gaps**:
  - Ctrl+C (graceful) and double Ctrl+C (force quit) are implemented
  - cancellation.py has full CancellationManager with timeout
  - DS_505_CANCELLED_BY_USER error code exists with exit code 130
  - None of this is in user-facing documentation
  - Missing: What happens to progress when you cancel?
  - Missing: How to resume after cancellation
- **Priority**: HIGH
- **Personas**: P1, P2

---

## Scenario 21: Troubleshooting

### 21.1 Windows-Specific Issues
- **User's Goal**: Use DeepScan on Windows
- **Current Doc Support**: PARTIAL
- **Key Gaps**:
  - SKILL.md troubleshooting mentions PYTHONIOENCODING
  - deepscan_engine.py has Windows UTF-8 fix
  - repl_executor.py documents `resource` module unavailability on Windows
  - Missing: Comprehensive Windows compatibility guide
  - Missing: What features are degraded on Windows (no resource limits)
- **Priority**: MEDIUM
- **Personas**: P1

### 21.2 Permission and Path Issues
- **User's Goal**: Fix file access errors
- **Current Doc Support**: PARTIAL
- **Key Gaps**:
  - Error codes DS_301 through DS_305 cover file/resource errors
  - Missing: Common permission scenarios and fixes
  - Missing: How symlinks are handled (documented in code but not for users)
- **Priority**: MEDIUM
- **Personas**: P1

---

## Cross-Cutting Observations

### Critical Gap: CLI vs Claude Code Distinction
The single most confusing aspect for new users is that DeepScan has two execution contexts:
1. **CLI mode** (running `python deepscan_engine.py` directly) - produces placeholders
2. **Claude Code mode** (triggered via `/deepscan` or natural language) - produces real analysis

This distinction is mentioned in multiple places but never clearly explained upfront. A dedicated section is needed.

### Critical Gap: End-to-End Walkthrough
No single document shows the complete workflow from installation to final results. USE_CASES.md comes closest with "End-to-End Scenarios" but assumes the reader already knows the concepts.

### Critical Gap: Error Code Reference
error_codes.py has a comprehensive error code system (DS-001 through DS-505) with remediation templates, but none of this is exposed in user-facing documentation.

### Documentation Architecture Observation
Current docs are organized by system component (ARCHITECTURE.md, SECURITY.md, SKILL.md) rather than by user journey. Best practices from developer tool documentation suggest organizing by:
1. Getting Started (tutorial)
2. How-To Guides (task-oriented)
3. Reference (API/command reference)
4. Explanation (concepts/architecture)

This is the Diataxis framework and would significantly improve usability.

### Strengths of Current Documentation
- USE_CASES.md is excellent for experienced users -- practical, well-organized
- SKILL.md has comprehensive command reference
- SECURITY.md is thorough for security audience
- Error code system is well-designed even though not user-facing yet
- HATEOAS hints in lazy mode output (next steps printed after init) are great UX

---

## Priority Summary for Documentation Improvements

### Must-Have (HIGH priority gaps)
1. Complete "Getting Started" tutorial with end-to-end walkthrough
2. Clear CLI vs Claude Code environment explanation (upfront, prominent)
3. Installation prerequisites and verification
4. Error recovery guide with common errors and fixes
5. REPL sandbox restrictions for users (not just security docs)
6. MAP phase step-by-step for Claude Code environment
7. Cancellation/resume workflow documentation
8. REDUCE phase documentation

### Should-Have (MEDIUM priority gaps)
1. Error code reference (extract from error_codes.py)
2. CLI shortcuts documentation
3. Incremental scanning workflow guide
4. Windows compatibility guide
5. Uninstallation instructions
6. Session overwrite protection explanation
7. Custom analysis in REPL guide

### Nice-to-Have (LOW priority gaps)
1. CI/CD integration guide
2. Output format documentation
3. Delta detection internals
4. Multi-session management best practices
5. Progress monitoring details
6. Deduplication/contradiction resolution guide
