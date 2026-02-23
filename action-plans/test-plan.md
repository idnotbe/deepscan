---
status: not-started
progress: "P0~P2 테스트 항목 정의 완료, 구현 미시작"
---

# DeepScan Test Plan

Prioritized test plan for the deepscan plugin. All source code lives in `.claude/skills/deepscan/scripts/`.

For security context, see [SECURITY.md](../.claude/skills/deepscan/docs/SECURITY.md).

---

## P0 -- CRITICAL (Security Bypass / Sandbox Escape)

These tests prevent sandbox escape, arbitrary file access, and denial of service. Must be implemented before any other testing work.

### 1. REPL Sandbox Escape Tests

**Target**: `repl_executor.py:105-117` (eval/exec in subprocess)

Must-block payloads (all should be rejected or produce no harmful effect):
- `__import__('os').system('id')` -- direct import
- `import os; os.system('id')` -- statement import
- `eval("__import__('os')")` -- nested eval
- `exec("import os")` -- nested exec
- `open('/etc/passwd').read()` -- file access
- `getattr(__builtins__, '__import__')('os')` -- dynamic attribute import
- `().__class__.__bases__[0].__subclasses__()` -- introspection chain to find file/os classes
- `type.__subclasses__(type)` -- via type() which is in SAFE_BUILTINS

### 2. SAFE_BUILTINS Introspection Chain Tests

**Target**: `constants.py:109-148` (SAFE_BUILTINS allowlist)

The allowlist includes `type`, `vars`, `dir`, `hasattr`, `callable`. These are known sandbox escape primitives. Tests must verify:
- `type.__subclasses__(type)` is blocked (by attribute check on `__subclasses__`)
- `vars(obj)` cannot expose `__globals__` or `__builtins__`
- `dir()` output cannot be used to chain to dangerous attributes
- `hasattr(obj, '__class__')` combined with attribute access is blocked
- No combination of allowed builtins can reach `os`, `sys`, `subprocess`, or `__import__`

### 3. Path Traversal Tests

**Targets**:
- `state_manager.py:381-398` (`_safe_write()` -- `resolve().relative_to()` containment)
- `checkpoint.py:96-115` (session hash validation)
- `ast_chunker.py:400-420` (project-root enforcement)

Test vectors (all must be rejected):
- `../../etc/passwd` -- classic traversal
- `/etc/passwd` -- absolute path
- Symlink pointing outside allowed directory
- Symlink chain (symlink -> symlink -> outside)
- Broken symlink
- Path with null bytes
- Windows-style path separators on Linux (`..\..\etc\passwd`)
- Unicode normalization tricks (e.g., combining characters)
- Very long path names (trigger ENAMETOOLONG to test error handling)

**Note**: SECURITY.md line 278 has an unchecked item: `[ ] Test for path traversal with .. and symlinks`. These tests directly address it.

### 4. Zombie Thread DoS Tests

**Targets**:
- `repl_executor.py:239-305` (helper-path thread execution)
- `deepscan_engine.py:511-516` (`uses_helpers` routing to thread timeout)

The helper execution path uses `ThreadPoolExecutor` -- threads cannot be killed on timeout. Tests must verify:
- `for i in range(10**12): pass` -- infinite loop via allowed AST nodes (For + Call + Name are all in whitelist)
- Large memory allocation: `x = [1] * 10**9`
- Verify that timeout returns control to caller even if thread continues
- Verify that AST validation blocks the most dangerous loop constructs from reaching the helper path
- Document which constructs can still cause zombie threads (known limitation)

### 5. Forbidden Pattern Regex Bypass Tests

**Target**: `deepscan_engine.py:344-367` (FORBIDDEN_PATTERNS)

Test bypass vectors:
- Whitespace insertion: `__imp ort__` (should this bypass regex?)
- Unicode lookalikes: `__\u0069mport__`
- String concatenation: `"__imp" + "ort__"`
- f-string interpolation: `f"{'__import__'}"`
- Comment injection: `__import__  # safe comment`
- Raw string: `r"__import__"`
- Multiline tricks

---

## P1 -- HIGH (Data Integrity / Defense in Depth)

### 6. Walker Symlink Safety Tests

**Target**: `walker.py:200-210` (follow_symlinks=False)

- Symlink directory should not be recursed into
- Symlink file should be skipped or handled safely
- Max depth enforcement (default and custom values)
- Max files limit enforcement
- Permission denied on directory -- should skip gracefully, not crash
- Race condition: symlink target changes between check and read (TOCTOU)

### 7. AST Chunker Robustness Tests

**Target**: `ast_chunker.py` (full module)

- File outside project root -- must be rejected (`ast_chunker.py:400-420`)
- Parser unavailable for language -- fallback to text chunking
- Malformed syntax (unclosed brackets, invalid encoding)
- Max depth enforcement
- Very large files (boundary of chunk size)
- Empty files
- Binary files misidentified as source

### 8. AST Whitelist Relaxation Tests

**Target**: `deepscan_engine.py:380-462` (ALLOWED_NODE_TYPES)

Recently added node types that widen attack surface:
- `ast.JoinedStr` / `ast.FormattedValue` (f-strings) -- verify `f"{__import__('os')}"` is still blocked
- `ast.Lambda` -- verify lambdas cannot access dangerous attributes
- Comprehensions (`ast.ListComp`, `ast.SetComp`, `ast.DictComp`, `ast.GeneratorExp`) -- verify cannot be used to iterate over dangerous objects

### 9. CI/CD Setup

- GitHub Actions workflow running pytest on push/PR
- Test on Linux (primary) and ideally Windows (for `resource` module fallback at `repl_executor.py:82-94`)
- Coverage reporting (target: security-critical modules at 90%+)

---

## P2 -- MEDIUM (Completeness / Robustness)

### 10. State/Checkpoint Integrity Tests

**Targets**:
- `state_manager.py` (full module)
- `checkpoint.py` (full module)

- Session hash validation rejects invalid hashes
- Checkpoint save/load round-trip preserves all data
- Corrupted checkpoint file handled gracefully
- Concurrent checkpoint writes don't corrupt state
- Cancellation during checkpoint write doesn't lose prior state

### 11. Aggregator Deduplication Tests

**Target**: `aggregator.py` (full module)

- Similarity threshold behavior at boundary (0.7 default)
- Identical findings deduplicated correctly
- Near-duplicate findings with different sources preserved
- Empty findings list handled
- Very large findings list performance

### 12. Error Code and Progress Tests

**Targets**:
- `error_codes.py` (full module)
- `progress.py` (full module)

- All error codes map to meaningful messages
- Progress streaming produces valid JSONL
- Progress percentages stay in 0-100 range

### 13. Resource Limit Tests (Cross-Platform)

**Target**: `repl_executor.py:82-94`

- Linux: `resource.setrlimit()` enforces memory/CPU limits
- Windows: verify graceful fallback when `resource` module unavailable
- Verify that absence of resource limits on Windows is documented/mitigated

---

## Test Infrastructure Needed

Before writing tests:

1. Create `tests/` directory with structure mirroring `scripts/`
2. Create `conftest.py` with shared fixtures (temp directories, mock state, etc.)
3. Create `pyproject.toml` with pytest configuration
4. Add `pytest` and `pytest-cov` as dev dependencies

```
tests/
  conftest.py
  test_repl_executor.py      # P0
  test_sandbox_escape.py      # P0 (SAFE_BUILTINS chains)
  test_path_traversal.py      # P0 (cross-module)
  test_forbidden_patterns.py  # P0
  test_walker.py              # P1
  test_ast_chunker.py         # P1
  test_ast_whitelist.py       # P1
  test_state_manager.py       # P2
  test_checkpoint.py          # P2
  test_aggregator.py          # P2
```

---

*Created: 2026-02-14*
*Based on: audit-deepscan.md, v1-security-review.md*
*Cross-validated with: Codex 5.3, vibe-check skill*
