# DeepScan Plugin

Deep multi-file analysis plugin for Claude Code. Uses chunked map-reduce with parallel sub-agents to analyze large codebases. Includes a sandboxed REPL executor for safe code evaluation.

## Repository Layout

| Path | Purpose |
|------|---------|
| `.claude/skills/deepscan/scripts/` | All Python source code (17 modules) |
| `.claude/skills/deepscan/docs/` | Architecture, security model, use cases |
| `.claude/skills/deepscan/SKILL.md` | Skill trigger and command reference |
| `.claude-plugin/plugin.json` | Plugin manifest (v0.1.0) |

## Testing

**All automated tests for this plugin live in this repository.**

**CRITICAL: No tests exist yet.** This plugin has zero test files, no `tests/` directory, no CI/CD pipeline, and no test runner configuration. The `.gitignore` includes pytest/coverage entries (`.pytest_cache/`, `htmlcov/`, `.coverage`), indicating testing was intended but never implemented.

### Intended Framework

- **pytest** -- referenced in internal docs as the intended test framework
- Tests should live in `tests/` mirroring the `scripts/` structure
- Run with: `pytest tests/`

### Security-Critical Code Requiring Tests

These modules enforce security boundaries and **must have tests before modification**:

| Module | Security Role |
|--------|--------------|
| `repl_executor.py` | Sandboxed `eval()`/`exec()` in subprocess; timeout enforcement |
| `deepscan_engine.py` | Forbidden pattern regex (lines 344-367), AST node whitelist (lines 368-460), dangerous attribute blocking |
| `constants.py` | `SAFE_BUILTINS` allowlist (lines 109-148) -- controls what's available in sandbox |
| `state_manager.py` | `_safe_write()` with `resolve().relative_to()` path containment (lines 381-398) |
| `walker.py` | File traversal with `follow_symlinks=False`, max depth enforcement |
| `ast_chunker.py` | Project-root enforcement via `resolve(strict=True)` + `relative_to()` (lines 400-420) |

### Known Gaps

- `SECURITY.md` (at `.claude/skills/deepscan/docs/SECURITY.md`) has an **unchecked checklist item**: `[ ] Test for path traversal with .. and symlinks` (line 278)
- Helper-path execution uses threads (not subprocesses) -- zombie thread DoS is a documented known limitation (`repl_executor.py:239-305`)
- `SAFE_BUILTINS` includes introspection primitives (`type`, `vars`, `dir`, `hasattr`) that need adversarial testing for sandbox escape chains
- No Windows testing for `resource` module fallback (`repl_executor.py:82-94`)

## Security Invariants

Treat REPL code, file paths, and chunk contents as **untrusted input**. Any change to sandbox policy requires:

1. Update to `.claude/skills/deepscan/docs/SECURITY.md`
2. Regression tests proving prior escape vectors remain blocked
3. Explicit review

Policy enforcement lives in:
- Forbidden patterns + AST whitelist + attribute blocking: `deepscan_engine.py:344-460`
- Builtins allowlist: `constants.py:109-148`
- Write path containment: `state_manager.py:381-398`
- Project-root enforcement: `ast_chunker.py:400-420`

## Documentation

- [README.md](README.md) -- Plugin overview and usage
- [SECURITY.md](.claude/skills/deepscan/docs/SECURITY.md) -- Threat model and defense-in-depth architecture
- [ARCHITECTURE.md](.claude/skills/deepscan/docs/ARCHITECTURE.md) -- System design
- [TEST-PLAN.md](TEST-PLAN.md) -- Prioritized test plan (P0/P1/P2)
