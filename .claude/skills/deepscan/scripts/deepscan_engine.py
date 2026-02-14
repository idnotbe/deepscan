#!/usr/bin/env python3
"""DeepScan REPL Engine - Phase 7.

Large context analysis system with parallel sub-agent processing.
Supports 100+ files or >1MB data using chunking and REPL-based analysis.

Phase 4 Features:
- Adaptive chunk sizing based on content type
- Model escalation (haiku → sonnet) on repeated failures
- Enhanced progress streaming with verbosity levels

Phase 5 Features:
- Incremental re-analysis via file hashing
- Only re-process changed files (3-7x speedup)
- Session-to-session delta detection

Phase 7 Features (Security & Performance Hardening):
- P7-001: REPL execution timeout with SafeREPLExecutor
- P7-002: ReDoS protection with safe_grep
- P7-003: Ghost findings cleanup (in aggregator)
- P7-004: Hash algorithm optimization (in incremental)

Usage:
    # Session management
    python deepscan_engine.py init <context_path> [-q "query"] [--adaptive] \\
        [--incremental --previous-session <hash>]
    python deepscan_engine.py status
    python deepscan_engine.py list
    python deepscan_engine.py resume [session_hash]
    python deepscan_engine.py abort <session_hash>
    python deepscan_engine.py clean [--older-than DAYS]

    # Analysis
    python deepscan_engine.py exec -c "<code>"
    python deepscan_engine.py map [-i/--instructions] [-v/--verbose]
    python deepscan_engine.py progress

    # Export
    python deepscan_engine.py export-results <output_path>
    python deepscan_engine.py reset
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
# P8-FIX: Removed unused 'Any' import

# Phase 6: Work Cancellation
from cancellation import (
    CancellationManager,
    get_cancellation_manager,
)
from checkpoint import CheckpointManager

# Phase 5: Incremental re-analysis
# P8-FIX: Removed unused imports (FileDelta, FileHashManifest, IncrementalAnalyzer)

# P1-FIX: Import aggregator for REDUCE phase integration
from aggregator import ResultAggregator

from models import (
    ChunkInfo,
    ChunkResult,
    # P8-FIX: Removed unused ContextMetadata, DeepScanConfig, FailureType
    DeepScanState,
    ScanMode,  # Issue 2: Use enum instead of string comparison
    SESSION_HASH_PATTERN,
)

# =============================================================================
# Phase 7: Security & Performance Hardening
# =============================================================================

# P7-FIX: Windows UTF-8 encoding fix (prevents UnicodeEncodeError with emojis)
# Must be done before any print() calls
import os

if sys.platform == "win32":
    # Force UTF-8 for stdout/stderr on Windows
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    # Also set environment variable for child processes
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")


# =============================================================================
# Module Imports (Phase 8: Large File Split)
# =============================================================================
# These modules were extracted from deepscan_engine.py for better maintainability.
# Dependency order: constants → grep_utils/state_manager/repl_executor/progress → helpers

# Constants and utilities (bottom layer - no internal imports)
from constants import (
    DEFAULT_EXEC_TIMEOUT,
    # P8-FIX: Removed unused MIN_CHUNKING_TIMEOUT, MAX_CHUNKING_TIMEOUT, TIMEOUT_PER_MB
    calculate_chunking_timeout,
    GREP_TIMEOUT,
    MAX_OUTPUT_SIZE,
    MAX_CLI_OUTPUT,
    MAX_CONTEXT_PREVIEW,
    MAX_GREP_CONTENT_SIZE,
    HELPER_NAMES,
    SAFE_BUILTINS,
    REDOS_PATTERNS,
    CHUNK_SIZE_BY_EXTENSION,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_PROGRESS_MAX_SIZE,
    WATCH_POLL_INTERVAL,
    truncate_output,
    detect_content_type,
)

# Grep utilities (depends on constants)
from grep_utils import (
    is_safe_regex,
    safe_grep,
)

# State management
from state_manager import StateManager

# REPL executor with timeout protection
from repl_executor import (
    SafeREPLExecutor,
    get_repl_executor,
    reset_global_state,
    _execute_with_thread_timeout,
)

# Progress tracking and escalation
from progress import (
    ProgressWriter,
    EscalationBudget,
    should_escalate,
    classify_failure,
    validate_session_hash,
)

# Helper functions for REPL context
from helpers import create_helpers


# =============================================================================
# Re-exports for backward compatibility
# =============================================================================
# The following are re-exported from their respective modules.
# Direct imports from the new modules are preferred.
__all__ = [
    # From models
    "SESSION_HASH_PATTERN",
    # From constants
    "DEFAULT_EXEC_TIMEOUT", "GREP_TIMEOUT", "MAX_OUTPUT_SIZE", "MAX_CLI_OUTPUT",
    "MAX_CONTEXT_PREVIEW", "MAX_GREP_CONTENT_SIZE", "HELPER_NAMES", "SAFE_BUILTINS",
    "REDOS_PATTERNS", "CHUNK_SIZE_BY_EXTENSION", "DEFAULT_CHUNK_SIZE",
    "DEFAULT_PROGRESS_MAX_SIZE", "truncate_output", "detect_content_type",
    # From grep_utils
    "is_safe_regex", "safe_grep",
    # From state_manager
    "StateManager",
    # From repl_executor (note: _execute_with_thread_timeout removed - private function)
    "SafeREPLExecutor", "get_repl_executor", "reset_global_state",
    # From progress
    "ProgressWriter", "EscalationBudget", "should_escalate", "classify_failure", "validate_session_hash",
    # From helpers
    "create_helpers",
]


# =============================================================================
# CLI Interface
# =============================================================================


def cmd_init(args: argparse.Namespace) -> int:
    """Initialize DeepScan state."""
    # P4.2-FIX: Session Overwrite Protection
    existing_session = StateManager.get_current_session_hash()
    force = getattr(args, "force", False)

    if existing_session and not force:
        print("[WARNING] Active session already exists:")
        print(f"  Session: {existing_session}")
        print("")
        print("Options:")
        print("  • Use --force to overwrite the existing session")
        print("  • Use 'deepscan resume' to continue the existing session")
        print("  • Use 'deepscan abort <session>' to delete it first")
        return 1

    manager = StateManager()
    adaptive = getattr(args, "adaptive", False)
    incremental = getattr(args, "incremental", False)
    previous_session = getattr(args, "previous_session", None)
    # Phase 1: Lazy Mode arguments
    lazy = getattr(args, "lazy", False)
    target = getattr(args, "target", None)
    depth = getattr(args, "depth", None)
    # P8-FIX: Agent type specialization (Issue 1 from deepscan_errors_20260124.md)
    agent_type = getattr(args, "agent_type", "general")

    state = manager.init(
        args.context_path,
        args.query,
        adaptive=adaptive,
        incremental=incremental,
        previous_session=previous_session,
        lazy=lazy,
        target=target,
        depth=depth,
        agent_type=agent_type,
    )

    print("[OK] DeepScan initialized")
    print(f"  Session: {state.session_id}")
    print(f"  Context: {state.context_meta.path if state.context_meta else 'N/A'}")
    print(f"  Size: {state.context_meta.total_size:,} characters" if state.context_meta else "")
    if state.context_meta and state.context_meta.is_directory:
        print(f"  Files: {state.context_meta.file_count}")

    # Phase 4: Show adaptive chunking info
    if state.config.adaptive_chunking:
        print(f"  [Adaptive] Content type: {state.config.detected_content_type}")
        print(f"  [Adaptive] Chunk size: {state.config.chunk_size:,} characters")

    # Phase 5: Show incremental analysis info
    if getattr(state.config, "incremental_enabled", False):
        changed_count = getattr(state.config, "changed_file_count", 0)
        deleted_count = getattr(state.config, "deleted_file_count", 0)
        prev_session = getattr(state.config, "previous_session", None)
        print("  [Incremental] Enabled")
        if prev_session:
            print(f"  [Incremental] Previous session: {prev_session[:16]}...")
        print(f"  [Incremental] Changed/added files: {changed_count}")
        print(f"  [Incremental] Deleted files: {deleted_count}")
        if changed_count == 0 and deleted_count == 0:
            print("  [Incremental] No changes detected - analysis can be skipped!")

    # P8-FIX: Show agent type if not default (Issue 1 from deepscan_errors_20260124.md)
    agent_type_config = getattr(state.config, "agent_type", "general")
    if agent_type_config != "general":
        print(f"  [Agent] Type: {agent_type_config}")

    # Phase 1: Show lazy mode info
    # Issue 2 FIX: Use ScanMode enum instead of string comparison
    scan_mode = getattr(state.config, "scan_mode", None)
    if scan_mode and scan_mode != ScanMode.FULL:
        print(f"  [Mode] {scan_mode.value.upper()}")
        if scan_mode == ScanMode.LAZY:
            print(f"  [Mode] Max depth: {state.config.lazy_depth}")
            print(f"  [Mode] File limit: {state.config.lazy_file_limit}")
        elif scan_mode == ScanMode.TARGETED:
            print(f"  [Mode] Targets: {', '.join(state.config.target_paths)}")

    # Phase 3: Lazy Mode - output tree view and HATEOAS hints
    # Issue 2 FIX: Use ScanMode enum
    # Issue 3 FIX: Use public property instead of private attribute access
    if scan_mode == ScanMode.LAZY and manager.lazy_tree_view:
        print("\n" + "=" * 60)
        print("📁 Lazy Mode Active (--lazy)")
        print("   Structure only. File contents not loaded.")
        print("=" * 60 + "\n")
        print(manager.lazy_tree_view)
        print("\n" + "-" * 60)
        print("💡 Next Steps:")
        context_path = state.context_meta.path if state.context_meta else "."
        print(f"  • View specific file: deepscan exec -c \"load_file('path/to/file.py')\"")
        print(f"  • Preview subdirectory: deepscan exec -c \"preview_dir('subdir')\"")
        print(f"  • Check mode: deepscan exec -c \"is_lazy_mode()\"")
        print(f"  • Full scan: deepscan init {context_path} (no --lazy)")
        print("-" * 60)

    return 0


def cmd_status(_args: argparse.Namespace) -> int:
    """Show current status."""
    del _args  # Required by argparse interface but unused
    # DEFECT-004 FIX: Get current session hash first
    session_hash = StateManager.get_current_session_hash()
    if not session_hash:
        print("[ERROR] No active session. Run 'deepscan init <path>' first.")
        return 1

    manager = StateManager(session_hash)

    try:
        state = manager.load()
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return 1

    print("=== DeepScan Status ===")
    print(f"Session:  {state.session_id}")
    print(f"Phase:    {state.phase}")
    print(f"Context:  {state.context_meta.total_size:,} chars" if state.context_meta else "N/A")
    print(f"Chunks:   {len(state.chunks)} total, {len(state.results)} processed")
    print(f"Progress: {state.progress_percent:.1f}%")
    print(f"Buffers:  {len(state.buffers)}")
    if state.final_answer:
        print("Answer:   (available)")
    return 0


def cmd_exec(args: argparse.Namespace) -> int:
    """Execute Python code in REPL context with sandboxing."""
    # P0-FIX: Get current session hash first (matching cmd_status pattern)
    session_hash = StateManager.get_current_session_hash()
    if not session_hash:
        print("[ERROR] No active session. Run 'deepscan init <path>' first.")
        return 1

    manager = StateManager(session_hash)

    try:
        manager.load()
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return 1

    # Create safe namespace
    content_str = manager.get_context()
    helpers = create_helpers(manager)

    namespace = {
        "__builtins__": SAFE_BUILTINS,
        "content": content_str,
        **helpers,
    }

    code = args.code

    # FIX-CVE-2026-003: Input length check to prevent ReDoS
    MAX_CODE_LENGTH = 100_000  # 100KB
    if len(code) > MAX_CODE_LENGTH:
        print(f"[ERROR] Code too long: {len(code)} bytes (max {MAX_CODE_LENGTH})")
        return 1

    # Layer 1: Forbidden pattern check
    FORBIDDEN_PATTERNS = [
        r"__import__",
        r"exec\s*\(",
        r"eval\s*\(",
        r"compile\s*\(",
        r"open\s*\(",
        r"os\.",
        r"subprocess",
        r"sys\.",  # FIX: Added missing pattern (prevents sys.exit, sys.modules)
        r"__globals__",
        r"__class__",
        r"__bases__",
        r"__closure__",  # FIX: Prevent closure introspection
        r"getattr\s*\(",
        r"setattr\s*\(",
        r"delattr\s*\(",  # FIX: Added missing pattern
    ]

    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, code):
            print(f"[ERROR] Forbidden pattern detected: {pattern}")
            return 1

    # Layer 2: AST validation
    import ast

    # SANDBOX_FIX: Initialize tree to None for reliable checking later
    tree: ast.Module | None = None

    try:
        tree = ast.parse(code, mode="exec")

        # P2-FIX: Strengthened AST whitelist - explicit DENY of dangerous nodes
        # BLOCKED (not in whitelist): FunctionDef, ClassDef, AsyncFunctionDef,
        # Import, ImportFrom, Global, Nonlocal, Yield, YieldFrom, Await, Try, Raise,
        # With, Assert, Match
        # P7-FIX: Allow comprehensions and lambda for practical analysis
        ALLOWED_NODE_TYPES = {
            ast.Module,
            ast.Expr,
            ast.Call,
            ast.Name,
            ast.Load,
            ast.Store,  # FIX-CVE-2026-001: CRITICAL - Enable variable assignment
            ast.Del,  # FIX-CVE-2026-001: CRITICAL - Enable deletion
            ast.Constant,
            ast.BinOp,
            ast.UnaryOp,
            ast.Compare,
            ast.Subscript,
            ast.List,
            ast.Tuple,
            ast.Dict,
            ast.Assign,
            ast.AugAssign,  # FIX: Enable +=, -=, etc.
            ast.For,
            ast.If,
            ast.IfExp,  # D4-FIX: Ternary expressions (x if y else z) - safe for analysis
            ast.Pass,
            ast.Attribute,
            ast.Add,
            ast.Sub,
            ast.Mult,
            ast.Div,
            ast.Mod,
            ast.Eq,
            ast.NotEq,
            ast.Lt,
            ast.Gt,
            ast.LtE,
            ast.GtE,
            ast.In,
            ast.NotIn,
            ast.And,
            ast.Or,
            ast.Not,
            # P8-FIX: Removed ast.Index (deprecated since Python 3.9, project requires 3.10+)
            # P7-FIX: Comprehensions (ast.walk checks nested nodes recursively)
            ast.ListComp,       # [x for x in y]
            ast.DictComp,       # {k: v for k, v in items}
            ast.SetComp,        # {x for x in y}
            ast.GeneratorExp,   # (x for x in y)
            ast.comprehension,  # for loop part of comprehensions
            # P7-FIX: Lambda expressions
            ast.Lambda,         # lambda x: x
            ast.arguments,      # lambda parameter list
            ast.arg,            # single parameter
            # P7-FIX: Keyword arguments in function calls
            ast.keyword,        # func(key=value)
            # P8-FIX: f-strings (Issue 2 from deepscan_errors_20260124.md)
            # SECURITY NOTE: ast.walk() recursively validates contents inside {}.
            # Dangerous code like f"{__import__('os')}" is blocked by existing
            # Attribute checks (lines 425-436) that block dunder attributes,
            # and FORBIDDEN_PATTERNS that block __import__.
            ast.JoinedStr,      # f"hello {name}"
            ast.FormattedValue, # the {name} part inside f-strings
        }

        # TYPE_NARROWING: Assert tree is not None (guaranteed by successful ast.parse above)
        assert tree is not None
        for node in ast.walk(tree):
            if type(node) not in ALLOWED_NODE_TYPES:
                print(f"[ERROR] Forbidden AST node: {type(node).__name__}")
                return 1

            # P2-FIX: Enhanced dangerous attribute access blocking
            if isinstance(node, ast.Attribute):
                # Block dunder attributes that could allow introspection escapes
                DANGEROUS_ATTRS = {
                    "__class__", "__bases__", "__subclasses__", "__mro__",
                    "__globals__", "__code__", "__closure__", "__func__",
                    "__self__", "__dict__", "__doc__", "__module__",
                    "__builtins__", "__import__", "__loader__", "__spec__",
                    "__annotations__", "__wrapped__", "__qualname__",
                }
                if node.attr.startswith("_") or node.attr in DANGEROUS_ATTRS:
                    print(f"[ERROR] Forbidden attribute: {node.attr}")
                    return 1
    except SyntaxError as e:
        # P8-FIX: Handle SyntaxError explicitly instead of swallowing
        print(f"[ERROR] Invalid Python syntax: {e}")
        return 1

    # P7-001 FIX: Determine if code uses helpers (requires main process execution)
    # HELPER_DETECTION_FIX: Use module-level HELPER_NAMES constant (ensures sync with create_helpers)
    # SANDBOX_FIX: Use explicit None check instead of "tree" in dir() (unreliable)
    uses_helpers = (
        any(isinstance(node, ast.Name) and node.id in HELPER_NAMES for node in ast.walk(tree))
        if tree is not None
        else False
    )

    # P8-FIX: Calculate appropriate timeout
    # Priority: 1) CLI-provided timeout, 2) auto-detect for I/O-heavy operations, 3) default
    cli_timeout = getattr(args, "timeout", None)
    if cli_timeout is not None:
        exec_timeout = cli_timeout
    elif "write_chunks" in code or "chunk_indices" in code:
        # I/O-heavy operation: calculate based on context size
        context_size = len(content_str) if content_str else 0
        exec_timeout = calculate_chunking_timeout(context_size)
        print(f"[INFO] Using dynamic timeout: {exec_timeout}s for {context_size:,} bytes")
    else:
        exec_timeout = DEFAULT_EXEC_TIMEOUT

    # Execute with appropriate method based on helper usage
    if not uses_helpers:
        # P7-001 FIX: Use SafeREPLExecutor for timeout protection (no helpers needed)
        # Create executor with content in namespace
        executor = get_repl_executor(timeout=exec_timeout)
        try:
            # Initialize namespace with content (picklable)
            executor.execute(f"content = {repr(content_str)}")
            result = executor.execute(code)
            if result is not None:
                # P4-FIX: Apply output budgeting to CLI output
                output = str(result) if not isinstance(result, str) else result
                print(truncate_output(output, MAX_CLI_OUTPUT))
        except TimeoutError as e:
            print(f"[ERROR] Execution timeout: {e}")
            return 1
        except RuntimeError as e:
            print(f"[ERROR] Execution error: {e}")
            return 1
        finally:
            executor.shutdown()
    else:
        # Main process execution (requires helpers with StateManager closure)
        # Note: grep helper uses safe_grep for ReDoS protection (P7-002)
        # P2-FIX: Use thread-based timeout wrapper for helper execution
        status, result = _execute_with_thread_timeout(code, namespace, exec_timeout)

        if status == "error":
            print(f"[ERROR] Execution error: {result}")
            return 1
        elif status == "eval_ok" and result is not None:
            # P4-FIX: Apply output budgeting to CLI output
            output = str(result) if not isinstance(result, str) else result
            print(truncate_output(output, MAX_CLI_OUTPUT))

    return 0


def cmd_reset(_args: argparse.Namespace) -> int:
    """Reset all state."""
    del _args  # Required by argparse interface but unused
    # P0-FIX: Get current session hash first (matching cmd_status pattern)
    session_hash = StateManager.get_current_session_hash()
    if not session_hash:
        print("[ERROR] No active session to reset.")
        return 1

    manager = StateManager(session_hash)
    manager.reset()
    print("[OK] DeepScan state reset")
    return 0


def cmd_export_results(args: argparse.Namespace) -> int:
    """Export results to file."""
    # P0-FIX: Get current session hash first (matching cmd_status pattern)
    session_hash = StateManager.get_current_session_hash()
    if not session_hash:
        print("[ERROR] No active session. Run 'deepscan init <path>' first.")
        return 1

    manager = StateManager(session_hash)

    try:
        state = manager.load()
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return 1

    output = {
        "session_id": state.session_id,
        "query": state.query,
        "results": [r.model_dump() for r in state.results],
        "buffers": state.buffers,
        "final_answer": state.final_answer,
    }

    out_path = Path(args.output_path)
    out_path.write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")
    print(f"[OK] Results exported to {out_path}")
    return 0


# =============================================================================
# Session Management Commands (FR-018.6)
# =============================================================================


def cmd_list(_args: argparse.Namespace) -> int:
    """List all DeepScan sessions."""
    del _args  # Required by argparse interface but unused
    sessions = StateManager.list_sessions()

    if not sessions:
        print("No DeepScan sessions found.")
        return 0

    print(f"=== DeepScan Sessions ({len(sessions)}) ===\n")
    print(f"{'Hash':<45} {'Phase':<12} {'Progress':<10} {'Modified'}")
    print("-" * 90)

    for s in sessions:
        modified_str = s["modified"].strftime("%Y-%m-%d %H:%M")
        print(f"{s['hash']:<45} {s['phase']:<12} {s['progress']:.1f}%{'':<5} {modified_str}")

    # Show current session
    current = StateManager.get_current_session_hash()
    if current:
        print(f"\n(Current: {current})")

    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    """Resume a DeepScan session."""
    session_hash = getattr(args, "session_hash", None)

    if not session_hash:
        # Resume most recent session
        sessions = StateManager.list_sessions()
        if not sessions:
            print("[ERROR] No sessions to resume.")
            return 1
        session_hash = sessions[0]["hash"]
        print(f"Resuming most recent session: {session_hash}")

    # SECURITY: Validate session_hash to prevent path traversal
    if not validate_session_hash(session_hash):
        print(f"[ERROR] Invalid session hash format: {session_hash}")
        return 1

    # Validate session exists
    session_dir = StateManager.DEFAULT_CACHE_ROOT / session_hash

    # SECURITY: Additional path traversal check
    try:
        resolved = session_dir.resolve()
        resolved.relative_to(StateManager.DEFAULT_CACHE_ROOT.resolve())
    except ValueError:
        print("[ERROR] Invalid session path")
        return 1

    if not session_dir.exists():
        print(f"[ERROR] Session not found: {session_hash}")
        return 1

    # Load and set as current
    manager = StateManager(session_hash=session_hash)
    try:
        state = manager.load()
    except FileNotFoundError:
        print(f"[ERROR] Invalid session (no state file): {session_hash}")
        return 1

    StateManager.set_current_session_hash(session_hash)

    # Check for checkpoint
    checkpoint_mgr = CheckpointManager(session_hash)
    checkpoint = checkpoint_mgr.load_checkpoint()

    print(f"[OK] Resumed session: {state.session_id}")
    print(f"  Phase: {state.phase}")
    print(f"  Progress: {state.progress_percent:.1f}%")
    print(f"  Chunks: {len(state.chunks)} total, {len(state.results)} processed")

    if checkpoint:
        ts = checkpoint.created_at.strftime("%Y-%m-%d %H:%M")
        print(f"  Checkpoint: batch {checkpoint.batch_index} ({ts})")

    return 0


def cmd_abort(args: argparse.Namespace) -> int:
    """Abort and delete a DeepScan session permanently."""
    import shutil

    session_hash = args.session_hash

    # SECURITY: Validate session_hash to prevent path traversal
    if not validate_session_hash(session_hash):
        print(f"[ERROR] Invalid session hash format: {session_hash}")
        return 1

    session_dir = StateManager.DEFAULT_CACHE_ROOT / session_hash

    # SECURITY: Additional path traversal check after resolution
    try:
        resolved = session_dir.resolve()
        resolved.relative_to(StateManager.DEFAULT_CACHE_ROOT.resolve())
    except ValueError:
        print("[ERROR] Invalid session path")
        return 1

    if not session_dir.exists():
        print(f"[ERROR] Session not found: {session_hash}")
        return 1

    # Confirm deletion
    shutil.rmtree(session_dir)
    print(f"[OK] Session aborted and removed: {session_hash}")

    # Clear current session if it was the aborted one
    current = StateManager.get_current_session_hash()
    if current == session_hash:
        StateManager.CURRENT_SESSION_FILE.unlink(missing_ok=True)

    return 0


def cmd_clean(args: argparse.Namespace) -> int:
    """Clean old sessions."""
    days = getattr(args, "older_than", 7)

    result = StateManager.gc_clean_old_sessions(max_age_days=days)
    freed_mb = result["freed_bytes"] / 1024 / 1024
    print(f"[OK] Cleaned {result['deleted']} sessions, freed {freed_mb:.2f} MB")
    return 0


# =============================================================================
# Phase 3: MAP Phase - Parallel Sub-Agent Processing
# =============================================================================


def process_map_phase(
    manager: StateManager,
    batch_size: int | None = None,
    sequential_fallback: bool = True,
    cancel_mgr: CancellationManager | None = None,
) -> dict:
    """Process chunks in MAP phase using parallel sub-agents.

    Spawns sub-agents in batches to process chunks concurrently.
    Falls back to sequential processing after consecutive failures.
    Supports graceful cancellation via CancellationManager (Phase 6).

    Args:
        manager: StateManager with loaded state.
        batch_size: Override batch size (default from config).
        sequential_fallback: Whether to fall back to sequential on failures.
        cancel_mgr: Optional CancellationManager for graceful cancellation.

    Returns:
        Dict with processing summary: processed, failed, skipped counts.
        Includes 'cancelled': True if cancelled by user.
    """

    if not manager.state:
        return {"error": "No active session", "processed": 0, "failed": 0}

    state = manager.state
    config = state.config
    batch_size = batch_size or config.max_parallel_agents

    # Get unprocessed chunks (by checking which chunk_ids are not in results)
    # CRITICAL-FIX: Exclude placeholder/pending from processed_ids
    # This allows re-running map in Claude Code after CLI testing generates placeholders
    # Without this fix, CLI placeholders would block future real analysis
    #
    # NOTE: "failed" is intentionally NOT excluded - failed chunks require explicit
    # retry via --escalate flag to prevent infinite error loops (vibe_check feedback)
    # "pending" is a placeholder variant from CLI parallel mode (line 955)
    # "placeholder" is from CLI sequential mode (line 1017)
    processed_ids = {
        r.chunk_id for r in state.results
        if r.status not in ("placeholder", "pending")
    }
    pending_chunks = [c for c in state.chunks if c.chunk_id not in processed_ids]

    if not pending_chunks:
        return {"message": "All chunks already processed", "processed": 0, "failed": 0}

    # Update phase
    state.phase = "map"
    manager.save()

    # Initialize tracking
    total_chunks = len(pending_chunks)
    processed_count = 0
    failed_count = 0
    placeholder_count = 0  # MEDIUM-3 FIX: Track placeholders separately
    consecutive_failures = 0
    use_sequential = False
    cancelled = False

    # Create checkpoint manager for batch saves
    checkpoint_mgr = CheckpointManager(manager.session_hash)

    # P1-FIX: Initialize ProgressWriter for real-time monitoring
    progress_writer = ProgressWriter(manager.state_dir)

    # Process in batches (with ProgressWriter context)
    with progress_writer:
        for batch_start in range(0, total_chunks, batch_size):
            # Phase 6: Check for cancellation before processing batch
            if cancel_mgr and cancel_mgr.is_cancelled():
                print("\n[CANCEL] Cancellation requested, saving progress...")
                cancelled = True
                break
            batch_end = min(batch_start + batch_size, total_chunks)
            batch_chunks = pending_chunks[batch_start:batch_end]
            batch_num = (batch_start // batch_size) + 1
            total_batches = (total_chunks + batch_size - 1) // batch_size

            # P1-FIX: Emit batch start event for progress monitoring
            progress_writer.emit_batch_start(batch_num, total_batches, len(batch_chunks))

            print(f"[MAP] Processing batch {batch_num}/{total_batches} ({len(batch_chunks)} chunks)")

            # Check if we should use sequential mode
            if use_sequential:
                batch_results = _process_batch_sequential(
                    batch_chunks, state, manager, batch_start, total_chunks
                )
            else:
                batch_results = _process_batch_parallel(
                    batch_chunks, state, manager, batch_start, total_chunks, config.timeout_seconds
                )

            # Process batch results
            batch_success = 0
            batch_failed = 0
            batch_placeholders = 0  # MEDIUM-3 FIX: Track placeholders per batch
            for result in batch_results:
                if result.get("status") == "failed":
                    batch_failed += 1
                    failed_count += 1
                elif result.get("status") in ("placeholder", "pending"):
                    # MEDIUM-3 FIX: Track placeholder results separately
                    try:
                        chunk_result = ChunkResult.model_validate(result)
                        # HIGH-FIX: Remove existing placeholder/pending for this chunk (idempotent update)
                        # Prevents duplicate results when re-running map
                        state.results = [
                            r for r in state.results
                            if r.chunk_id != chunk_result.chunk_id or r.status not in ("placeholder", "pending")
                        ]
                        state.results.append(chunk_result)
                        batch_placeholders += 1
                        placeholder_count += 1
                        processed_count += 1  # Still count as processed for progress
                    except Exception as e:
                        print(f"[WARN] Failed to validate placeholder result: {e}")
                        failed_count += 1
                        batch_failed += 1
                else:
                    # Add to state results (real analysis success)
                    try:
                        chunk_result = ChunkResult.model_validate(result)
                        # HIGH-FIX: Remove ALL existing results for this chunk (idempotent update)
                        # Real results should replace any prior result (placeholder, pending, OR failed)
                        # This handles the --escalate retry scenario where failed → success
                        # Without this, failed + success would coexist causing reduce phase confusion
                        state.results = [
                            r for r in state.results
                            if r.chunk_id != chunk_result.chunk_id
                        ]
                        state.results.append(chunk_result)
                        batch_success += 1
                        processed_count += 1
                        # P1-FIX: Emit chunk completion and findings
                        progress_writer.emit_chunk_complete(
                            chunk_result.chunk_id,
                            len(chunk_result.findings),
                            chunk_result.status  # P8-FIX: Use actual status instead of hardcoded "completed"
                        )
                        for finding in chunk_result.findings:
                            # FIX: Use correct field names (point, confidence) from Finding model
                            progress_writer.emit_finding(
                                chunk_result.chunk_id,
                                finding.point[:100],
                                finding.confidence
                            )
                    except Exception as e:
                        print(f"[WARN] Failed to validate result: {e}")
                        failed_count += 1
                        batch_failed += 1

            # Update progress
            completed = len(state.results)
            state.progress_percent = (completed / len(state.chunks) * 100) if state.chunks else 0

            # Save checkpoint after batch (with cancellation check)
            checkpoint_mgr.save_checkpoint(state, batch_num, cancel_mgr=cancel_mgr)
            manager.save()

            # P1-FIX: Emit batch end event
            progress_writer.emit_batch_end(batch_num, batch_success, batch_failed)

            # MEDIUM-3 FIX: Include placeholder count in batch summary
            if batch_placeholders > 0:
                print(f"[MAP] Batch {batch_num}: {batch_success} success, {batch_placeholders} placeholders, {batch_failed} failed")
            else:
                print(f"[MAP] Batch {batch_num}: {batch_success} success, {batch_failed} failed")

            # Phase 6: Check for cancellation after batch completion
            if cancel_mgr and cancel_mgr.is_cancelled():
                print("\n[CANCEL] Cancellation requested after batch, saving progress...")
                cancelled = True
                break

            # Check for high failure rate (graceful degradation)
            # Trigger on >50% failure rate (not just 100%)
            failure_rate = batch_failed / len(batch_chunks) if batch_chunks else 0
            if failure_rate > 0.5:
                consecutive_failures += 1
                if consecutive_failures >= 2 and sequential_fallback and not use_sequential:
                    print("[WARN] 2 consecutive high-failure batches, switching to sequential")
                    use_sequential = True
                    consecutive_failures = 0  # Reset for sequential mode
            else:
                consecutive_failures = 0

    # Phase 6: Final save on cancellation
    if cancelled:
        # Pass cancel_mgr to allow Force Quit (double tap) to interrupt hung save
        checkpoint_mgr.save_checkpoint(state, -1, cancel_mgr=cancel_mgr)
        manager.save()
        # CRITICAL: Mark graceful shutdown as completed to prevent timeout force quit
        # Without this call, the timeout thread would force-quit even after successful save
        if cancel_mgr:
            cancel_mgr.mark_completed()
        # Show resume instructions
        CancellationManager.show_resume_instructions(manager.session_hash)

    # Update phase on completion (if not cancelled)
    if not cancelled and failed_count == 0:
        state.phase = "reduce"
    manager.save()

    return {
        "processed": processed_count,
        "failed": failed_count,
        "placeholders": placeholder_count,  # MEDIUM-3 FIX: Include placeholder count
        "total": total_chunks,
        "mode": "sequential" if use_sequential else "parallel",
        "cancelled": cancelled,
        "session_hash": manager.session_hash if cancelled else None,
    }


def _process_batch_parallel(  # pyright: ignore[reportUnusedParameter]
    batch_chunks: list[ChunkInfo],
    state: DeepScanState,
    manager: StateManager,
    batch_start: int,
    total_chunks: int,
    _timeout_seconds: int,
) -> list[dict]:
    """Process a batch of chunks in parallel using Task tool.

    Note: This function generates the prompts but relies on the calling
    context (Claude Code) to spawn the actual sub-agents via Task tool.
    For testing/CLI, falls back to sequential processing.

    Args:
        batch_chunks: Chunks to process in this batch.
        state: Current DeepScan state.
        manager: StateManager for context access.
        batch_start: Starting index for progress display.
        total_chunks: Total number of chunks for progress display.
        _timeout_seconds: Timeout for each sub-agent. Currently unused in CLI mode
            which only generates placeholder results. Will be used when Claude Code
            environment spawns real sub-agents via Task tool.

    Returns:
        List of chunk results.
    """
    from subagent_prompt import generate_subagent_prompt

    # NOTE: CLI warning moved to cmd_map() to print once (not per batch)
    # See LOW-1 fix in ERROR_REPORT_DEEPSCAN_SKILLS.md

    # In CLI mode, we can't actually spawn Task tool agents
    # Generate prompts and process sequentially as fallback
    # Real parallel processing happens when this is called from Claude Code context

    results = []
    context = manager.get_context()
    query = state.query or "Analyze this content"
    # P8-FIX: Get agent_type from config (Issue 1 from deepscan_errors_20260124.md)
    agent_type = getattr(state.config, "agent_type", "general")

    for i, chunk in enumerate(batch_chunks):
        chunk_num = batch_start + i + 1

        # Get chunk content
        chunk_content = context[chunk.start_offset : chunk.end_offset]

        # Generate prompt (for logging/debugging)
        prompt = generate_subagent_prompt(
            chunk=chunk,
            chunk_content=chunk_content,
            query=query,
            chunk_number=chunk_num,
            total_chunks=total_chunks,
            agent_type=agent_type,  # P8-FIX: Pass agent_type to subagent
        )

        # In standalone CLI mode, we process sequentially
        # When called from Claude Code, this prompt would be used with Task tool
        print(f"[MAP] Chunk {chunk_num}/{total_chunks}: {chunk.chunk_id}")

        # Create a placeholder result for CLI mode
        # Real results come from sub-agent responses when run in Claude Code
        result = {
            "chunk_id": chunk.chunk_id,
            "status": "pending",
            "findings": [],
            "missing_info": ["Requires Claude Code Task tool for parallel processing"],
            "partial_answer": None,
            "_prompt_length": len(prompt),
        }
        results.append(result)

    return results


def _process_batch_sequential(
    batch_chunks: list[ChunkInfo],
    state: DeepScanState,
    manager: StateManager,
    batch_start: int,
    total_chunks: int,
) -> list[dict]:
    """Process a batch sequentially (fallback mode).

    Used when parallel processing fails or for CLI-only execution.

    Args:
        batch_chunks: Chunks to process in this batch.
        state: Current DeepScan state.
        manager: StateManager for context access.
        batch_start: Starting index for progress display.
        total_chunks: Total number of chunks for progress display.

    Returns:
        List of chunk results.
    """
    from subagent_prompt import create_sequential_prompt

    # V2-FIX: Sequential fallback notification (CLI warning already printed in cmd_map)
    print("\n[INFO] Sequential fallback mode activated (parallel processing unavailable).\n")

    results = []
    context = manager.get_context()
    query = state.query or "Analyze this content"

    for i, chunk in enumerate(batch_chunks):
        chunk_num = batch_start + i + 1

        # Get chunk content
        chunk_content = context[chunk.start_offset : chunk.end_offset]

        # Generate simplified prompt
        create_sequential_prompt(
            chunk=chunk,
            chunk_content=chunk_content,
            query=query,
        )

        print(f"[SEQ] Chunk {chunk_num}/{total_chunks}: {chunk.chunk_id}")

        # Create placeholder result for CLI mode
        result = {
            "chunk_id": chunk.chunk_id,
            "status": "placeholder",  # P0-FIX: Changed from "pending" to "placeholder"
            "findings": [],
            "missing_info": ["CLI mode - no actual analysis performed"],
            "partial_answer": None,
        }
        results.append(result)

    return results


def generate_map_instructions(
    manager: StateManager,
    model: str = "haiku",
    failed_chunks_only: bool = False,
    limit: int = 5,
    batch_num: int | None = None,
) -> str:
    """Generate instructions for Claude Code to execute MAP phase.

    This returns a formatted instruction block that Claude Code can use
    to spawn parallel sub-agents via the Task tool.

    Args:
        manager: StateManager with loaded state.
        model: Model to use for sub-agents ("haiku" or "sonnet" for escalation).
        failed_chunks_only: If True, only generate instructions for failed chunks.
        limit: Maximum number of chunk prompts to include (default: 5).
            Issue #5 FIX: Prevents terminal truncation for large chunk counts.
        batch_num: If specified, show only this batch (1-indexed).
            Issue #5 FIX: Allows pagination through batches.

    Returns:
        Formatted instruction string for parallel processing.
    """
    from subagent_prompt import generate_subagent_prompt

    if not manager.state:
        return "ERROR: No active session"

    state = manager.state
    config = state.config

    # Get chunks to process
    processed_ids = {r.chunk_id for r in state.results}
    failed_ids = {r.chunk_id for r in state.results if r.status == "failed"}

    if failed_chunks_only:
        # Re-process only failed chunks with escalated model
        pending_chunks = [c for c in state.chunks if c.chunk_id in failed_ids]
        mode_label = f"RETRY with {model}"
    else:
        pending_chunks = [c for c in state.chunks if c.chunk_id not in processed_ids]
        mode_label = "NEW"

    if not pending_chunks:
        if failed_chunks_only:
            return "No failed chunks to retry."
        return "All chunks have been processed. Run 'reduce' to aggregate results."

    context = manager.get_context()
    query = state.query or "Analyze this content"
    total_chunks = len(pending_chunks)

    # Issue #5 FIX: Calculate batches for pagination
    batch_size = config.max_parallel_agents
    total_batches = (total_chunks + batch_size - 1) // batch_size

    # Determine which chunks to show based on batch_num parameter
    if batch_num is not None:
        # Show specific batch only
        if batch_num < 1 or batch_num > total_batches:
            return f"ERROR: Invalid batch number {batch_num}. Valid range: 1-{total_batches}"
        start_idx = (batch_num - 1) * batch_size
        end_idx = min(start_idx + batch_size, total_chunks)
        batch_chunks = pending_chunks[start_idx:end_idx]
        batch_label = f"Batch {batch_num}/{total_batches}"
    else:
        # Show first batch (original behavior), but respect limit
        batch_chunks = pending_chunks[:min(batch_size, limit)]
        batch_label = f"Batch 1/{total_batches} (showing {len(batch_chunks)} of {batch_size})"

    # Phase 4: Model escalation info
    escalation_note = ""
    if model == "sonnet":
        escalation_note = "\n**[ESCALATED]** Using sonnet model for complex chunks.\n"

    # P8-FIX: Get agent_type from config (Issue 1 from deepscan_errors_20260124.md)
    agent_type = getattr(config, "agent_type", "general")
    agent_type_note = ""
    if agent_type != "general":
        agent_type_note = f"\n**[Agent Type]** Using specialized {agent_type} analysis.\n"

    # Issue #5 FIX: Show pagination info
    pagination_note = ""
    if total_batches > 1:
        pagination_note = (
            f"\n**[Pagination]** Showing {batch_label}. "
            f"Use `--batch N` to view batch N, or `--output file.md` to save all.\n"
        )

    instructions = f"""## MAP Phase Instructions ({mode_label})

**Session**: {manager.session_hash}
**Query**: {query}
**Total Pending Chunks**: {total_chunks}
**Total Batches**: {total_batches}
**Batch Size**: {batch_size}
{escalation_note}{agent_type_note}{pagination_note}
### {batch_label}: Spawn {len(batch_chunks)} Sub-Agents in Parallel

Use the Task tool with these parameters for each chunk:

```
subagent_type: "general-purpose"
model: "{model}"
```

> **Note**: Omit `run_in_background` (defaults to foreground) for stable output retrieval.
> Parallel execution is achieved by calling multiple Task tools in a single message.

### Chunk Prompts:

"""
    # Issue #5 FIX: Apply limit to prevent terminal truncation
    display_chunks = batch_chunks[:limit] if batch_num is None else batch_chunks
    truncated = len(batch_chunks) > len(display_chunks)

    for i, chunk in enumerate(display_chunks):
        chunk_num = (batch_num - 1) * batch_size + i + 1 if batch_num else i + 1
        chunk_content = context[chunk.start_offset : chunk.end_offset]
        prompt = generate_subagent_prompt(
            chunk=chunk,
            chunk_content=chunk_content,
            query=query,
            chunk_number=chunk_num,
            total_chunks=total_chunks,
            agent_type=agent_type,  # P8-FIX: Pass agent_type to subagent
        )

        # Truncate for display
        content_preview = chunk_content[:200] + "..." if len(chunk_content) > 200 else chunk_content

        instructions += f"""
#### Chunk {chunk_num}: {chunk.chunk_id}
- Byte range: {chunk.start_offset} - {chunk.end_offset}
- Content preview: {content_preview[:100]}...

<prompt>
{prompt}
</prompt>

---
"""

    # Issue #5 FIX: Indicate if output was truncated
    if truncated:
        remaining = len(batch_chunks) - len(display_chunks)
        instructions += f"\n**[TRUNCATED]** {remaining} more chunks not shown. Use `--limit {len(batch_chunks)}` or `--output file.md` to see all.\n\n"

    instructions += """
### After All Sub-Agents Complete

1. Collect results from each background task
2. Parse JSON responses
3. Run: `python deepscan_engine.py exec -c "add_result({...})"`  for each result
4. Continue with next batch or proceed to REDUCE phase
"""

    return instructions


def cmd_map(args: argparse.Namespace) -> int:
    """Execute MAP phase (parallel chunk processing).

    Phase 6: Supports graceful cancellation via Ctrl+C.
    - First Ctrl+C: Finish current batch, save checkpoint, exit gracefully
    - Second Ctrl+C: Force quit immediately
    """
    session_hash = StateManager.get_current_session_hash()
    if not session_hash:
        print("[ERROR] No active session. Run 'init' first or 'resume' a session.")
        return 1

    # Create manager with session hash and load state
    manager = StateManager(session_hash)
    try:
        manager.load()
    except FileNotFoundError:
        print(f"[ERROR] Failed to load session: {session_hash}")
        return 1

    # Phase 4: Model escalation support
    show_instructions = getattr(args, "instructions", False)
    escalate = getattr(args, "escalate", False)
    # Issue #5 FIX: New pagination and output options
    output_file = getattr(args, "output", None)
    batch_num = getattr(args, "batch", None)
    limit = getattr(args, "limit", 5)

    if show_instructions or escalate:
        # Determine model and mode
        if escalate:
            model = "sonnet"
            failed_only = True
            print("[ESCALATE] Generating instructions to retry failed chunks with sonnet model...")
        else:
            model = "haiku"
            failed_only = False

        # Issue #5 FIX: Pass pagination parameters
        instructions = generate_map_instructions(
            manager,
            model=model,
            failed_chunks_only=failed_only,
            limit=limit,
            batch_num=batch_num,
        )

        # Issue #5 FIX: Handle output file option
        if output_file:
            output_path = Path(output_file)
            output_path.write_text(instructions, encoding="utf-8")
            print(f"[OK] Instructions written to {output_path}")
            print(f"     Total chunks: {len(manager.state.chunks) if manager.state else 0}")
        else:
            print(instructions)
        return 0

    # Phase 6: Set up cancellation manager
    # NOTE: Do NOT perform I/O or lock acquisition in signal handler callbacks!
    # This could cause deadlocks if signal arrives while StateManager._lock is held.
    # The main loop in process_map_phase handles checkpoint saving safely.
    cancel_mgr = get_cancellation_manager(
        graceful_timeout=30.0,  # 30s to complete current batch
        on_graceful=None,  # Safe: no I/O in signal handler (avoids deadlock)
        reset=True,  # Fresh manager for each command
    )

    # LOW-1 FIX + D3-FIX: Enhanced CLI warning with clear next steps
    print("\n" + "=" * 65)
    print("[IMPORTANT] CLI MODE - NO REAL ANALYSIS WILL BE PERFORMED")
    print("=" * 65)
    print("DeepScan requires Claude Code environment for actual analysis.")
    print("Running in CLI mode generates PLACEHOLDER results only.\n")
    print("To perform real analysis:")
    print("  1. Run: deepscan map --instructions")
    print("  2. Copy the generated Task tool prompts")
    print("  3. Execute them in Claude Code (with model: 'sonnet' for best quality)")
    print("  4. Or save to file: deepscan map --instructions -o prompts.md")
    print("=" * 65 + "\n")

    # Run MAP phase with cancellation support
    result = process_map_phase(manager, cancel_mgr=cancel_mgr)

    if "error" in result:
        print(f"[ERROR] {result['error']}")
        return 1

    # Phase 6: Handle cancellation result
    if result.get("cancelled"):
        print("\n[MAP CANCELLED]")
        print(f"  Processed before cancel: {result['processed']}")
        print(f"  Failed: {result['failed']}")
        print(f"\n[HINT] Resume with: deepscan resume {result['session_hash']}")
        return 130  # Exit code for SIGINT cancellation

    # HIGH-2 FIX: Distinguish between real analysis and placeholder results
    placeholder_count = result.get("placeholders", 0)
    real_count = result["processed"] - placeholder_count

    if placeholder_count > 0 and real_count == 0:
        # All results are placeholders (CLI mode)
        print("\n[MAP SIMULATION COMPLETE]")
        print(f"  Real Analysis:   0")
        print(f"  Placeholders:    {placeholder_count} (run in Claude Code for full results)")
        print(f"  Failed:          {result['failed']}")
        print(f"  Mode:            {result['mode']}")
        print("\n[HINT] Use 'map --instructions' to get prompts for Claude Code Task tool.")
    else:
        # Some or all real results
        print("\n[MAP COMPLETE]")
        print(f"  Real Analysis:   {real_count}")
        if placeholder_count > 0:
            print(f"  Placeholders:    {placeholder_count}")
        print(f"  Failed:          {result['failed']}")
        print(f"  Mode:            {result['mode']}")

        if result["failed"] > 0:
            print("\n[HINT] Some chunks failed. Run 'map' again to retry or use 'map --instructions'")

    return 0


def cmd_reduce(_args: argparse.Namespace) -> int:
    """Execute REDUCE phase - aggregate findings from all chunks.

    P1-FIX: Integrates the previously orphaned aggregator.py module.
    """
    del _args  # Required by argparse interface but unused
    session_hash = StateManager.get_current_session_hash()
    if not session_hash:
        print("[ERROR] No active session. Run 'init' first or 'resume' a session.")
        return 1

    manager = StateManager(session_hash)
    try:
        manager.load()
    except FileNotFoundError:
        print(f"[ERROR] Failed to load session: {session_hash}")
        return 1

    state = manager.state
    if not state.results:
        print("[ERROR] No chunk results to aggregate. Run 'map' first.")
        return 1

    # V1-FIX + Issue 2 FIX: Filter out placeholders before aggregation
    # Aggregator should only receive real analysis results (SRP compliance)
    real_results = [r for r in state.results if r.status not in ("placeholder", "pending")]
    placeholder_count = len(state.results) - len(real_results)

    if placeholder_count > 0:
        if not real_results:
            # Issue #6 FIX: Block reduce if all results are placeholders
            # This prevents user confusion about "0 findings" when no analysis occurred
            print("\n" + "=" * 60)
            print("[ERROR] Cannot run REDUCE - all results are placeholders!")
            print("=" * 60)
            print("\nThis happens when 'map' was run in CLI mode (outside Claude Code).")
            print("CLI mode generates placeholder results for testing, not real analysis.\n")
            print("To perform actual analysis:")
            print("  1. Use 'map --instructions' to get Task tool prompts")
            print("  2. Execute those prompts in Claude Code environment")
            print("  3. Or use 'map --instructions -o prompts.md' to save to file\n")
            print(f"Session: {session_hash}")
            print(f"Placeholders: {placeholder_count} chunks (no real findings)")
            return 1
        else:
            print(f"\n[INFO] Aggregating {len(real_results)} real results (skipping {placeholder_count} placeholders).")

    # Get deleted files from incremental analysis (if available)
    deleted_files: list[str] = []
    if hasattr(state.config, "deleted_file_count") and state.config.deleted_file_count > 0:
        if manager._file_delta:
            deleted_files = manager._file_delta.deleted_files

    # Create aggregator and run REDUCE (Issue 2 FIX: pass only real_results)
    aggregator = ResultAggregator(similarity_threshold=0.7)
    result = aggregator.aggregate_findings(
        chunk_results=real_results,  # Filtered: no placeholders
        original_query=state.query or "",
        deleted_files=deleted_files,
    )

    # Display results
    print("\n[REDUCE COMPLETE]")
    print(f"  Total findings: {result['total_findings']}")
    print(f"  Unique findings: {result['unique_findings']}")
    print(f"  Deduplication: {result['deduplication_ratio']:.1%}")
    if result["filtered_deleted_files"] > 0:
        print(f"  Ghost findings filtered: {result['filtered_deleted_files']}")

    if result["needs_manual_review"]:
        print(f"\n[WARNING] {len(result['contradictions'])} contradictions detected - manual review needed")
        for contradiction in result["contradictions"][:3]:  # Show first 3
            print(f"    - {contradiction}")

    # Show top findings
    print("\n[TOP FINDINGS]")
    for i, finding in enumerate(result["aggregated_findings"][:10], 1):
        f = finding["finding"]
        support = finding["support_count"]
        confidence = finding["confidence"]
        summary = f.point[:60] + "..." if len(f.point) > 60 else f.point
        print(f"  {i}. [{confidence}] {summary} (from {support} chunk(s))")

    # Store aggregated results in state
    state.final_answer = json.dumps(result, default=str, indent=2)
    state.phase = "reduce"
    manager.save()

    print(f"\n[OK] Aggregated results saved. Export with: export-results output.json")
    return 0


def cmd_progress(args: argparse.Namespace) -> int:
    """Show detailed progress for current session."""
    # P5.3-FIX: Watch mode support
    watch_mode = getattr(args, "watch", False)
    session_hash = StateManager.get_current_session_hash()
    if not session_hash:
        print("[ERROR] No active session.")
        return 1

    manager = StateManager(session_hash)
    try:
        manager.load()
    except FileNotFoundError:
        print(f"[ERROR] Failed to load session: {session_hash}")
        return 1

    state = manager.state

    # P5.3-FIX: Watch mode - poll progress.jsonl for real-time updates
    if watch_mode:
        import time as time_module

        progress_file = manager.state_dir / "progress.jsonl"
        last_size = 0
        poll_interval = WATCH_POLL_INTERVAL  # from constants.py

        print(f"[WATCH] Monitoring progress (Ctrl+C to stop)...")
        print(f"  Session: {session_hash}")
        print(f"  File: {progress_file}\n")

        try:
            while True:
                try:
                    # Reload state to get latest progress
                    manager.load()
                    state = manager.state

                    total_chunks = len(state.chunks)
                    completed_chunks = len(state.results)
                    failed_chunks = sum(1 for r in state.results if r.status == "failed")
                    pending_chunks = total_chunks - completed_chunks

                    # Check for new progress.jsonl entries
                    new_entries = []
                    if progress_file.exists():
                        current_size = progress_file.stat().st_size
                        if current_size > last_size:
                            with progress_file.open("r", encoding="utf-8") as f:
                                f.seek(last_size)
                                for line in f:
                                    line = line.strip()
                                    if line:
                                        try:
                                            entry = json.loads(line)
                                            new_entries.append(entry)
                                        except json.JSONDecodeError:
                                            pass
                            last_size = current_size

                    # Display update
                    timestamp = time_module.strftime("%H:%M:%S")
                    print(f"\r[{timestamp}] Phase: {state.phase} | "
                          f"Progress: {state.progress_percent:.1f}% | "
                          f"Chunks: {completed_chunks}/{total_chunks} "
                          f"(+{len(new_entries)} events)", end="", flush=True)

                    # Show new findings if any
                    for entry in new_entries:
                        if entry.get("type") == "finding":
                            print(f"\n  >> Finding: {entry.get('point', '')[:60]}...")

                    time_module.sleep(poll_interval)
                except KeyboardInterrupt:
                    print("\n\n[OK] Watch mode stopped.")
                    return 0
        except Exception as e:
            print(f"\n[ERROR] Watch mode error: {e}")
            return 1

    # Static progress display (original behavior)
    total_chunks = len(state.chunks)
    completed_chunks = len(state.results)
    failed_chunks = sum(1 for r in state.results if r.status == "failed")
    pending_chunks = total_chunks - completed_chunks

    print(f"\n[PROGRESS] Session: {session_hash}")
    print(f"  Phase: {state.phase}")
    print(f"  Progress: {state.progress_percent:.1f}%")
    print(f"  Chunks: {completed_chunks}/{total_chunks} completed")
    print(f"  - Success: {completed_chunks - failed_chunks}")
    print(f"  - Failed: {failed_chunks}")
    print(f"  - Pending: {pending_chunks}")

    if state.query:
        print(f"  Query: {state.query[:50]}{'...' if len(state.query) > 50 else ''}")

    # Show recent results
    if state.results:
        print("\n[RECENT RESULTS]")
        for r in state.results[-3:]:
            findings_count = len(r.findings)
            print(f"  - {r.chunk_id}: {r.status} ({findings_count} findings)")

    return 0


def _expand_cli_shortcuts(argv: list[str]) -> list[str]:
    """Expand CLI shortcuts to full commands (P4-FIX: FR-018.5).

    Shortcuts:
        ? -> status
        ! "code" -> exec -c "code"
        + -> resume
        + hash -> resume hash
        x -> abort (requires session hash)
        x hash -> abort hash

    Args:
        argv: Original sys.argv list.

    Returns:
        Expanded argument list.
    """
    if len(argv) < 2:
        return argv

    cmd = argv[1]

    # ? = status
    if cmd == "?":
        return [argv[0], "status"] + argv[2:]

    # ! "code" = exec -c "code"
    if cmd == "!":
        if len(argv) >= 3:
            return [argv[0], "exec", "-c", argv[2]] + argv[3:]
        else:
            return [argv[0], "exec", "-c", ""]

    # + = resume
    if cmd == "+":
        if len(argv) >= 3:
            return [argv[0], "resume", argv[2]] + argv[3:]
        else:
            return [argv[0], "resume"]

    # x = abort (cancel)
    if cmd == "x":
        if len(argv) >= 3:
            return [argv[0], "abort", argv[2]] + argv[3:]
        else:
            # Need session hash for abort, return as-is to show error
            return [argv[0], "abort"]

    # Check if first arg is a path (shortcut for init)
    # If command is not a known subcommand and looks like a path, treat as init
    known_commands = {
        "init", "status", "exec", "reset", "export-results",
        "list", "resume", "abort", "clean", "map", "progress", "reduce",
        "?", "!", "+", "x",
    }
    if cmd not in known_commands and (Path(cmd).exists() or cmd.startswith(".") or "/" in cmd or "\\" in cmd):
        # Treat as: deepscan init <path>
        return [argv[0], "init"] + argv[1:]

    return argv


def main() -> int:
    """Main CLI entry point."""
    # P4-FIX: Expand CLI shortcuts (FR-018.5)
    expanded_argv = _expand_cli_shortcuts(sys.argv)
    if expanded_argv != sys.argv:
        sys.argv = expanded_argv

    parser = argparse.ArgumentParser(description="DeepScan REPL Engine - Phase 1 MVP")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # init
    init_parser = subparsers.add_parser("init", help="Initialize state")
    init_parser.add_argument("context_path", help="Path to context file or directory")
    init_parser.add_argument("-q", "--query", help="Initial query")
    init_parser.add_argument(
        "-a",
        "--adaptive",
        action="store_true",
        help="Enable adaptive chunk sizing based on content type (Phase 4)",
    )
    init_parser.add_argument(
        "--incremental",
        action="store_true",
        help="Enable incremental re-analysis - only process changed files (Phase 5)",
    )
    init_parser.add_argument(
        "--previous-session",
        help="Session hash to compare against for delta detection (requires --incremental)",
    )
    # Phase 1: Lazy Mode arguments
    init_parser.add_argument(
        "--lazy",
        action="store_true",
        help="Use lazy mode: show structure only, don't load file contents",
    )
    init_parser.add_argument(
        "--target",
        type=str,
        action="append",
        help="Target specific path(s) for analysis (can be repeated)",
    )
    init_parser.add_argument(
        "--depth",
        type=int,
        default=3,
        help="Max directory depth for lazy traversal (default: 3)",
    )
    # P8-FIX: Agent type specialization (Issue 1 from deepscan_errors_20260124.md)
    init_parser.add_argument(
        "--agent-type",
        type=str,
        choices=["general", "security", "architecture", "performance"],
        default="general",
        help="Specialized analysis type: general (default), security, architecture, or performance",
    )
    # P4.2-FIX: Session overwrite protection
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing session if one is active",
    )
    init_parser.set_defaults(func=cmd_init)

    # status
    status_parser = subparsers.add_parser("status", help="Show status")
    status_parser.set_defaults(func=cmd_status)

    # exec
    exec_parser = subparsers.add_parser("exec", help="Execute code")
    exec_parser.add_argument("-c", "--code", required=True, help="Code to execute")
    exec_parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=None,
        help="Execution timeout in seconds (default: 5 for simple commands, auto-calculated for write_chunks)",
    )
    exec_parser.set_defaults(func=cmd_exec)

    # reset
    reset_parser = subparsers.add_parser("reset", help="Reset state")
    reset_parser.set_defaults(func=cmd_reset)

    # export-results
    export_parser = subparsers.add_parser("export-results", help="Export results")
    export_parser.add_argument("output_path", help="Output file path")
    export_parser.set_defaults(func=cmd_export_results)

    # Session management commands (FR-018.6)
    list_parser = subparsers.add_parser("list", help="List all sessions")
    list_parser.set_defaults(func=cmd_list)

    resume_parser = subparsers.add_parser("resume", help="Resume a session")
    resume_parser.add_argument(
        "session_hash", nargs="?", help="Session to resume (default: most recent)"
    )
    resume_parser.set_defaults(func=cmd_resume)

    abort_parser = subparsers.add_parser("abort", help="Abort and delete a session")
    abort_parser.add_argument("session_hash", help="Session to abort")
    abort_parser.set_defaults(func=cmd_abort)

    clean_parser = subparsers.add_parser("clean", help="Clean old sessions")
    clean_parser.add_argument("--older-than", type=int, default=7, help="Days (default: 7)")
    clean_parser.set_defaults(func=cmd_clean)

    # Phase 3: MAP phase commands
    map_parser = subparsers.add_parser("map", help="Run MAP phase (parallel chunk processing)")
    map_parser.add_argument(
        "--instructions",
        "-i",
        action="store_true",
        help="Show instructions for Claude Code Task tool",
    )
    map_parser.add_argument(
        "--escalate",
        "-e",
        action="store_true",
        help="Generate instructions to retry failed chunks with sonnet model (does not execute, use in Claude Code)",
    )
    # Issue #5 FIX: Add pagination and output options for large chunk counts
    map_parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Write instructions to file instead of stdout",
    )
    map_parser.add_argument(
        "--batch",
        type=int,
        help="Show specific batch number only (1-indexed)",
    )
    map_parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Max chunks to show in instructions (default: 5)",
    )
    map_parser.set_defaults(func=cmd_map)

    progress_parser = subparsers.add_parser("progress", help="Show detailed progress")
    # P5.3-FIX: Watch mode for real-time monitoring
    progress_parser.add_argument(
        "--watch",
        "-w",
        action="store_true",
        help="Watch progress in real-time (polls progress.jsonl every 2 seconds)",
    )
    progress_parser.set_defaults(func=cmd_progress)

    # P1-FIX: Add reduce command for REDUCE phase (aggregator integration)
    reduce_parser = subparsers.add_parser("reduce", help="Run REDUCE phase (aggregate findings)")
    reduce_parser.set_defaults(func=cmd_reduce)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
