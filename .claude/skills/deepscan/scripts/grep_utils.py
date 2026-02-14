"""DeepScan Grep Utilities Module.

ReDoS-protected grep functionality with process isolation.
"""

from __future__ import annotations

__all__ = [
    # Public functions
    "is_safe_regex",
    "safe_grep",
    # Note: _grep_worker is private (internal use only)
]

import re
from multiprocessing import Process, Queue
from queue import Empty

from constants import (
    GREP_TIMEOUT,
    MAX_GREP_CONTENT_SIZE,
    REDOS_PATTERNS,
)


def is_safe_regex(pattern: str) -> bool:
    """Check if regex pattern is potentially dangerous.

    Uses heuristic detection of common ReDoS patterns.
    This is a pre-filter; process isolation provides the actual protection.

    Args:
        pattern: Regex pattern to check.

    Returns:
        True if pattern appears safe, False if potentially dangerous.
    """
    for danger_pattern in REDOS_PATTERNS:
        try:
            if re.search(danger_pattern, pattern):
                return False
        except re.error:
            continue
    return True


def _grep_worker(
    pattern: str,
    content: str,
    max_matches: int,
    window: int,
    result_queue: Queue,
) -> None:
    """Worker process for isolated regex execution.

    Runs in separate process so it can be terminated if stuck.
    """
    try:
        results = []
        for m in re.finditer(pattern, content):
            start, end = m.span()
            snippet_start = max(0, start - window)
            snippet_end = min(len(content), end + window)

            results.append(
                {
                    "match": m.group(0),
                    "span": (start, end),
                    "snippet": content[snippet_start:snippet_end],
                }
            )

            if len(results) >= max_matches:
                break

        result_queue.put(("ok", results))
    except re.error as e:
        result_queue.put(("regex_error", str(e)))
    except Exception as e:
        result_queue.put(("error", f"{type(e).__name__}: {e}"))


def safe_grep(
    pattern: str,
    content: str,
    max_matches: int = 20,
    window: int = 100,
    timeout: int = GREP_TIMEOUT,
) -> list[dict]:
    """Search content with regex, protected against ReDoS.

    Two-layer protection:
    1. Heuristic pattern validation (fast, catches common cases)
    2. Process isolation with terminate (reliable, catches all cases)

    Args:
        pattern: Regex pattern to search for.
        content: Text content to search in.
        max_matches: Maximum number of matches to return.
        window: Characters of context around each match.
        timeout: Maximum seconds for regex execution.

    Returns:
        List of match dictionaries with match, span, snippet.

    Raises:
        ValueError: If pattern is detected as potentially dangerous.
        ValueError: If content exceeds size limit.
        TimeoutError: If regex execution times out.
        RuntimeError: If regex is invalid or execution fails.
    """
    # Layer 1: Heuristic pre-filter
    if not is_safe_regex(pattern):
        raise ValueError(
            "Potentially dangerous regex pattern rejected. "
            "Pattern contains nested quantifiers or similar ReDoS risks."
        )

    # Content size limit
    # Issue #4 FIX: Improved error message with actionable alternatives
    if len(content) > MAX_GREP_CONTENT_SIZE:
        size_mb = len(content) / (1024 * 1024)
        limit_mb = MAX_GREP_CONTENT_SIZE / (1024 * 1024)
        raise ValueError(
            f"Content too large for grep: {size_mb:.1f}MB (max {limit_mb:.1f}MB).\n"
            f"Alternatives:\n"
            f"  1. Use grep_file('pattern', 'path/to/file') to search specific files\n"
            f"  2. Use --lazy mode with load_file() for targeted searches\n"
            f"  3. Use --target to limit analysis scope\n"
            f"  4. Use peek_head()/peek_tail() to preview content sections"
        )

    # Layer 2: Process isolation
    result_queue: Queue = Queue()
    proc = Process(
        target=_grep_worker,
        args=(pattern, content, max_matches, window, result_queue),
        daemon=True,
    )
    proc.start()
    proc.join(timeout=timeout)

    if proc.is_alive():
        # Timeout - forcibly terminate
        proc.terminate()
        proc.join(timeout=1)
        if proc.is_alive():
            proc.kill()
            proc.join(timeout=1)
        raise TimeoutError(
            f"Regex execution timed out after {timeout}s. "
            f"Pattern may be causing catastrophic backtracking."
        )

    # Get result
    try:
        status, result = result_queue.get_nowait()
    except Empty as err:
        raise RuntimeError("Worker process terminated unexpectedly") from err

    if status == "regex_error":
        raise RuntimeError(f"Invalid regex pattern: {result}")
    if status == "error":
        raise RuntimeError(result)

    return result
