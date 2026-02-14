"""DeepScan Constants Module.

Shared constants, configurations, and utility functions used across deepscan modules.
This is the bottom layer of the dependency graph - no imports from other deepscan modules.
"""

from __future__ import annotations

__all__ = [
    # Timeout & Size Limits
    "DEFAULT_EXEC_TIMEOUT",
    "MIN_CHUNKING_TIMEOUT",
    "MAX_CHUNKING_TIMEOUT",
    "TIMEOUT_PER_MB",
    "GREP_TIMEOUT",
    "MAX_OUTPUT_SIZE",
    "MAX_CLI_OUTPUT",
    "MAX_CONTEXT_PREVIEW",
    "MAX_GREP_CONTENT_SIZE",
    # Helper Names
    "HELPER_NAMES",
    # Security
    "SAFE_BUILTINS",
    "REDOS_PATTERNS",
    # Chunking
    "CHUNK_SIZE_BY_EXTENSION",
    "DEFAULT_CHUNK_SIZE",
    # Progress
    "DEFAULT_PROGRESS_MAX_SIZE",
    "WATCH_POLL_INTERVAL",
    # Lazy Mode
    "DEFAULT_LAZY_DEPTH",
    "DEFAULT_LAZY_FILE_LIMIT",
    "DEFAULT_TREE_VIEW_LIMIT",
    # Chunk Count Safety Limits
    "MAX_RECOMMENDED_CHUNKS",
    "MAX_ABSOLUTE_CHUNKS",
    # Utility functions
    "truncate_output",
    "detect_content_type",
    "calculate_chunking_timeout",
]

from collections import Counter
from collections.abc import Iterable
from pathlib import Path

# =============================================================================
# Timeout & Size Limits
# =============================================================================

# P7-001: REPL Execution Timeout
# Default for simple commands (peek, grep, status)
DEFAULT_EXEC_TIMEOUT = 5  # seconds

# P8-FIX: Dynamic timeout for write_chunks and other I/O-heavy operations
# Formula: max(MIN_CHUNKING_TIMEOUT, context_size_mb * TIMEOUT_PER_MB)
# Capped at MAX_CHUNKING_TIMEOUT to prevent runaway timeouts
MIN_CHUNKING_TIMEOUT = 30  # seconds - minimum for any chunking operation
MAX_CHUNKING_TIMEOUT = 120  # seconds - hard cap to prevent indefinite hangs
TIMEOUT_PER_MB = 2  # seconds per megabyte of context

# P7-002: ReDoS Protection
GREP_TIMEOUT = 10  # seconds

# P4-FIX: Output Budgeting (prevent oversized outputs causing memory issues)
MAX_OUTPUT_SIZE = 500_000  # 500KB max output for any single operation
MAX_CLI_OUTPUT = 100_000  # 100KB max for CLI display
MAX_CONTEXT_PREVIEW = 50_000  # 50KB max for peek operations
MAX_GREP_CONTENT_SIZE = 5_000_000  # 5MB limit per grep

# =============================================================================
# Helper Function Names
# =============================================================================

# Helper function names available in REPL context.
# IMPORTANT: This MUST match the keys returned by create_helpers().
# The create_helpers() function validates this at runtime to catch desync.
HELPER_NAMES: frozenset[str] = frozenset(
    {
        "peek",
        "peek_head",
        "peek_tail",
        "grep",
        "grep_file",  # Issue 4 FIX: File-specific grep for lazy mode
        "chunk_indices",
        "write_chunks",
        "add_buffer",
        "get_buffers",
        "clear_buffers",
        "add_result",
        "add_results_from_file",  # D6-FIX: Batch import from JSON
        "set_phase",
        "set_final_answer",
        "get_status",
        "context_length",
        # Phase 3: Lazy Mode helpers
        "is_lazy_mode",
        "get_tree_view",
        "preview_dir",
        "load_file",
    }
)

# =============================================================================
# REPL Sandbox
# =============================================================================

# Safe builtins for REPL sandbox (no dangerous functions like exec, eval, open, import)
SAFE_BUILTINS: dict = {
    "len": len,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
    "tuple": tuple,
    "set": set,
    "print": print,
    "range": range,
    "enumerate": enumerate,
    "zip": zip,
    "map": map,
    "filter": filter,
    "min": min,
    "max": max,
    "sum": sum,
    "sorted": sorted,
    "reversed": reversed,
    "abs": abs,
    "round": round,
    "isinstance": isinstance,
    "type": type,
    "repr": repr,
    "True": True,
    "False": False,
    "None": None,
    "all": all,
    "any": any,
    "slice": slice,
    # P7-FIX: Introspection for debugging (getattr still blocked via FORBIDDEN_PATTERNS)
    "dir": dir,
    "vars": vars,
    "hasattr": hasattr,
    "callable": callable,
    "id": id,
}

# =============================================================================
# ReDoS Protection Patterns
# =============================================================================

# Enhanced ReDoS detection patterns
# Covers: basic, non-capturing, named groups, alternation
REDOS_PATTERNS: list[str] = [
    # Nested quantifiers (classic ReDoS)
    r"\([^)]*\+\)\+",  # (a+)+
    r"\([^)]*\*\)\+",  # (a*)+
    r"\([^)]*\+\)\*",  # (a+)*
    r"\([^)]*\*\)\*",  # (a*)*
    # Non-capturing group variants
    r"\(\?:[^)]*\+\)\+",  # (?:a+)+
    r"\(\?:[^)]*\*\)\+",  # (?:a*)+
    # Named group variants
    r"\(\?P<[^>]+>[^)]*\+\)\+",  # (?P<name>a+)+
    r"\(\?P<[^>]+>[^)]*\*\)\+",  # (?P<name>a*)+
    # Alternation with overlap
    r"\([^)]*\|[^)]*\)\+",  # (a|a)+
    r"\([^)]*\|[^)]*\)\*",  # (a|a)*
    # Character class in nested quantifier
    r"\(\[[^\]]+\]\+\)\+",  # ([a-z]+)+
    # Unbounded repetition patterns
    r"\(\.\*\)\{",  # (.*){n}
    r"\([^)]+\)\{[0-9]+,\}",  # (pattern){n,}
]

# =============================================================================
# Chunk Size Configuration (Phase 4: Adaptive Chunking)
# =============================================================================

# Chunk size by file extension (in characters)
# Code: smaller chunks (high token density, context-sensitive)
# Docs: larger chunks (low density, prose flows well)
# Config: smallest chunks (very high density)
CHUNK_SIZE_BY_EXTENSION: dict[str, int] = {
    # Code files (high density)
    ".py": 100_000,
    ".java": 100_000,
    ".ts": 100_000,
    ".tsx": 100_000,
    ".js": 100_000,
    ".jsx": 100_000,
    ".go": 100_000,
    ".rs": 100_000,
    ".c": 100_000,
    ".cpp": 100_000,
    ".h": 100_000,
    ".hpp": 100_000,
    ".cs": 100_000,
    ".rb": 100_000,
    ".php": 100_000,
    ".swift": 100_000,
    ".kt": 100_000,
    # Config/data (very high density)
    ".json": 80_000,
    ".yaml": 80_000,
    ".yml": 80_000,
    ".toml": 80_000,
    ".xml": 100_000,
    ".sql": 100_000,
    # Documentation (low density)
    ".md": 200_000,
    ".txt": 250_000,
    ".rst": 200_000,
    ".html": 150_000,
}

DEFAULT_CHUNK_SIZE = 150_000

# =============================================================================
# Progress Tracking
# =============================================================================

DEFAULT_PROGRESS_MAX_SIZE = 10 * 1024 * 1024  # 10MB

# P5.3-FIX: Watch mode polling interval (seconds)
# Configurable here for maintainability instead of hardcoded in deepscan_engine.py
WATCH_POLL_INTERVAL = 2  # seconds between progress.jsonl polls

# =============================================================================
# Lazy Mode Configuration (Phase 1)
# =============================================================================

# Maximum directory depth for lazy traversal
DEFAULT_LAZY_DEPTH = 3

# Maximum files to display in lazy mode before truncation
DEFAULT_LAZY_FILE_LIMIT = 50

# Safety cap for generate_tree_view to prevent memory exhaustion
# This limits the maximum number of entries (files + directories) that can be
# collected for tree view rendering, even if max_files is set higher or None.
# SYNC WARNING: Also defined in walker.py for standalone usage.
# If you change this value, update walker.py as well.
DEFAULT_TREE_VIEW_LIMIT = 10_000

# =============================================================================
# Chunk Count Safety Limits (Issue #2 Fix)
# =============================================================================

# Warn user when chunk count exceeds this threshold (API cost awareness)
# At 100 chunks with typical LLM pricing, costs can exceed $10-50
MAX_RECOMMENDED_CHUNKS = 100

# Hard limit to prevent runaway API costs and potential OOM errors
# At 500 chunks, processing becomes impractical (hours of API calls)
MAX_ABSOLUTE_CHUNKS = 500

# =============================================================================
# Utility Functions
# =============================================================================


def calculate_chunking_timeout(context_size_bytes: int) -> int:
    """Calculate dynamic timeout for chunking operations based on context size.

    P8-FIX: Prevents timeout errors on large contexts (e.g., 51MB → 346 chunks).
    Formula: max(MIN_CHUNKING_TIMEOUT, context_size_mb * TIMEOUT_PER_MB)
    Capped at MAX_CHUNKING_TIMEOUT to prevent indefinite hangs.

    Args:
        context_size_bytes: Total context size in bytes.

    Returns:
        Timeout in seconds (between MIN_CHUNKING_TIMEOUT and MAX_CHUNKING_TIMEOUT).

    Examples:
        >>> calculate_chunking_timeout(1_000_000)   # 1MB → 30s (minimum)
        30
        >>> calculate_chunking_timeout(51_000_000)  # 51MB → 102s
        102
        >>> calculate_chunking_timeout(100_000_000) # 100MB → 120s (capped)
        120
    """
    context_size_mb = context_size_bytes / (1024 * 1024)
    calculated = int(context_size_mb * TIMEOUT_PER_MB)
    return max(MIN_CHUNKING_TIMEOUT, min(calculated, MAX_CHUNKING_TIMEOUT))


def truncate_output(
    text: str,
    max_size: int = MAX_OUTPUT_SIZE,
    suffix: str = "\n... [TRUNCATED: output exceeded {max_size:,} characters] ...",
) -> str:
    """Truncate text to maximum size with informative suffix.

    P4-FIX: Prevents memory issues from oversized outputs.

    Args:
        text: Text to potentially truncate.
        max_size: Maximum allowed characters.
        suffix: Suffix to append (supports {max_size} placeholder).

    Returns:
        Original text if under limit, or truncated with suffix.
    """
    if len(text) <= max_size:
        return text

    formatted_suffix = suffix.format(max_size=max_size)
    # Reserve space for suffix
    truncate_at = max_size - len(formatted_suffix)
    if truncate_at < 100:
        truncate_at = 100  # Minimum content

    return text[:truncate_at] + formatted_suffix


def detect_content_type(path: Path, file_extensions: Iterable[str]) -> tuple[str, int]:
    """Detect dominant content type and recommended chunk size.

    Phase 4: Adaptive chunk sizing based on content characteristics.

    Args:
        path: Context path (file or directory).
        file_extensions: Iterable of file extensions found in context (list, set, etc.).

    Returns:
        Tuple of (content_type_description, recommended_chunk_size).
    """
    # Convert to list to support both set and list inputs
    ext_list = list(file_extensions) if file_extensions else []
    if not ext_list:
        return ("unknown", DEFAULT_CHUNK_SIZE)

    # Count extensions (Counter works with list, counting occurrences)
    ext_counts = Counter(ext_list)
    dominant_ext, count = ext_counts.most_common(1)[0]

    # Get chunk size for dominant extension
    chunk_size = CHUNK_SIZE_BY_EXTENSION.get(dominant_ext.lower(), DEFAULT_CHUNK_SIZE)

    # Determine content type category
    code_extensions = {".py", ".java", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".c", ".cpp"}
    config_extensions = {".json", ".yaml", ".yml", ".toml", ".xml"}
    doc_extensions = {".md", ".txt", ".rst", ".html"}

    if dominant_ext.lower() in code_extensions:
        content_type = f"code:{dominant_ext}"
    elif dominant_ext.lower() in config_extensions:
        content_type = f"config:{dominant_ext}"
    elif dominant_ext.lower() in doc_extensions:
        content_type = f"docs:{dominant_ext}"
    else:
        content_type = f"other:{dominant_ext}"

    return (content_type, chunk_size)
