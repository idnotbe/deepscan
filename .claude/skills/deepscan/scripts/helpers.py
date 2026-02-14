"""DeepScan Helpers Module.

Helper functions injected into the REPL namespace for context manipulation.
"""

from __future__ import annotations

__all__ = [
    # Main factory function
    "create_helpers",
    # Internal flag (for conditional imports)
    "AST_CHUNKER_AVAILABLE",
]

import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Any

from constants import (
    DEFAULT_LAZY_DEPTH,
    DEFAULT_LAZY_FILE_LIMIT,
    HELPER_NAMES,
    MAX_ABSOLUTE_CHUNKS,
    MAX_CONTEXT_PREVIEW,
    MAX_RECOMMENDED_CHUNKS,
    truncate_output,
)
from grep_utils import safe_grep
from models import ChunkInfo, ChunkResult, LazyModeError, ScanMode
from walker import default_should_prune, generate_tree_view

# P1-FIX: Import ast_chunker for semantic chunking (Strategy Pattern)
try:
    from ast_chunker import SemanticChunk, chunk_file_ast, fallback_text_chunk

    AST_CHUNKER_AVAILABLE = True
except ImportError:
    AST_CHUNKER_AVAILABLE = False

if TYPE_CHECKING:
    from state_manager import StateManager


def create_helpers(manager: StateManager) -> dict[str, Any]:
    """Create helper functions for REPL execution.

    Args:
        manager: StateManager instance for context access.

    Returns:
        Dictionary of helper functions to inject into REPL namespace.
    """

    def peek(start: int = 0, end: int | None = None) -> str:
        """View a portion of the context.

        P4-FIX: Enforces MAX_CONTEXT_PREVIEW budget to prevent oversized outputs.

        Args:
            start: Start index (negative for from end).
            end: End index (None for to end).

        Returns:
            Substring of context, truncated if exceeding budget.
            In lazy mode, returns informative message instead of empty string.
        """
        # FIX Issue 1: Lazy mode returns informative message to prevent hallucinations
        if is_lazy_mode():
            return (
                "[LAZY MODE] Global context is not loaded.\n"
                "Use get_tree_view() to see file structure.\n"
                "Use load_file('path/to/file') to view specific content."
            )

        content = manager.get_context()
        if start < 0:
            start = max(0, len(content) + start)
        if end is None:
            end = min(start + 3000, len(content))

        # P4-FIX: Enforce output budget
        result = content[start:end]
        return truncate_output(result, MAX_CONTEXT_PREVIEW)

    def peek_head(n: int = 3000) -> str:
        """View first n characters (max MAX_CONTEXT_PREVIEW)."""
        # P4-FIX: Cap at MAX_CONTEXT_PREVIEW
        n = min(n, MAX_CONTEXT_PREVIEW)
        return peek(0, n)

    def peek_tail(n: int = 3000) -> str:
        """View last n characters (max MAX_CONTEXT_PREVIEW)."""
        # P4-FIX: Cap at MAX_CONTEXT_PREVIEW
        n = min(n, MAX_CONTEXT_PREVIEW)
        return peek(-n)

    def grep(pattern: str, max_matches: int = 20, window: int = 100) -> list[dict]:
        """Search context with regex.

        Uses safe_grep for ReDoS protection (P7-002).

        Args:
            pattern: Regex pattern.
            max_matches: Maximum results.
            window: Characters of context around match.

        Returns:
            List of match dictionaries with match, span, snippet.

        Raises:
            LazyModeError: If called in lazy mode (context not loaded).
            ValueError: If pattern is detected as potentially dangerous ReDoS.
            TimeoutError: If regex execution times out.
        """
        # FIX Issue 4: Raise clear exception in lazy mode with recovery instructions
        if is_lazy_mode():
            raise LazyModeError(
                "grep() requires global context which is not loaded in lazy mode. "
                "Use grep_file(pattern, 'path/to/file') to search specific files, "
                "or use get_tree_view() to find files first."
            )

        content = manager.get_context()
        return safe_grep(pattern, content, max_matches, window)

    def chunk_indices(size: int = 150000, overlap: int = 0) -> list[tuple[int, int]]:
        """Calculate chunk boundaries.

        Args:
            size: Characters per chunk (50K-300K).
            overlap: Overlap between chunks (0-50K, must be < size).

        Returns:
            List of (start, end) tuples.

        Raises:
            ValueError: If parameters are out of valid range.
            LazyModeError: If called in lazy mode (context not loaded).
        """
        # Phase 4 FIX: Lazy mode guard - chunking requires loaded context
        if is_lazy_mode():
            raise LazyModeError(
                "chunk_indices() requires global context which is not loaded in lazy mode. "
                "Use targeted mode (--target) or full initialization to enable chunking."
            )

        # FIX-CRITICAL-BUG: Validate parameters to prevent infinite loop
        if not (50_000 <= size <= 300_000):
            raise ValueError(f"chunk_size must be 50K-300K, got {size}")
        if not (0 <= overlap <= 50_000):
            raise ValueError(f"chunk_overlap must be 0-50K, got {overlap}")
        if overlap >= size:
            raise ValueError(f"chunk_overlap ({overlap}) must be < chunk_size ({size})")

        content = manager.get_context()
        n = len(content)
        spans = []
        step = size - overlap  # Now guaranteed positive

        for start in range(0, n, step):
            end = min(n, start + size)
            spans.append((start, end))
            if end >= n:
                break

        return spans

    def write_chunks(
        out_dir: str | None = None,
        size: int = 150000,
        overlap: int = 0,
        semantic: bool = False,
    ) -> list[str]:
        """Write context chunks to files.

        P1-FIX: Added semantic chunking support (Strategy Pattern).
        When semantic=True, uses AST-based chunking for code files
        with automatic fallback to character-based chunking on errors.

        Args:
            out_dir: Output directory (defaults to cache/chunks).
            size: Characters per chunk (50K-300K).
            overlap: Overlap between chunks (0-50K, must be < size).
            semantic: If True, use AST-based semantic chunking (P1-FIX).

        Returns:
            List of created file paths.

        Raises:
            ValueError: If parameters are out of valid range.
            LazyModeError: If called in lazy mode without semantic chunking.
        """
        # Phase 4 FIX: Lazy mode guard (unless semantic chunking which reads files directly)
        if is_lazy_mode() and not semantic:
            raise LazyModeError(
                "write_chunks() requires global context which is not loaded in lazy mode. "
                "Use semantic=True for AST-based chunking, or use targeted/full mode."
            )

        # P8-FIX: Path traversal protection (Issue 6 from deepscan_errors_20260124.md)
        # Validate out_dir to prevent directory creation outside session sandbox
        if out_dir:
            # Force out_dir to be relative to state_dir (blocks absolute paths and ..)
            out_path = (manager.state_dir / out_dir).resolve()
            state_dir_resolved = manager.state_dir.resolve()
            # Security check: ensure resolved path is within session directory
            try:
                out_path.relative_to(state_dir_resolved)
            except ValueError:
                raise ValueError(
                    f"out_dir must be within session directory. "
                    f"Got path that resolves outside: {out_dir}"
                )
        else:
            out_path = manager.state_dir / "chunks"
        out_path.mkdir(parents=True, exist_ok=True)

        paths = []
        chunk_infos = []

        # P1-FIX: Strategy Pattern - try semantic chunking if requested
        if semantic and AST_CHUNKER_AVAILABLE and manager.state and manager.state.context_meta:
            context_path = Path(manager.state.context_meta.path)
            if context_path.is_dir():
                try:
                    print("[CHUNK] Using semantic (AST-based) chunking...")
                    semantic_chunks: list[SemanticChunk] = []

                    for source_file in context_path.rglob("*"):
                        if source_file.is_file() and source_file.suffix in {
                            ".py",
                            ".js",
                            ".ts",
                            ".java",
                            ".go",
                            ".rs",
                            ".c",
                            ".cpp",
                            ".h",
                        }:
                            try:
                                file_chunks = chunk_file_ast(
                                    source_file,
                                    max_chunk_chars=size,
                                    project_root=context_path,
                                )
                                semantic_chunks.extend(file_chunks)
                            except Exception as e:
                                # Fallback per file
                                print(
                                    f"[WARN] AST failed for {source_file.name}, "
                                    f"using text fallback: {e}"
                                )
                                try:
                                    fallback_chunks = fallback_text_chunk(
                                        source_file, size, context_path
                                    )
                                    semantic_chunks.extend(fallback_chunks)
                                except Exception:
                                    pass

                    if semantic_chunks:
                        for i, sc in enumerate(semantic_chunks):
                            chunk_file = out_path / f"chunk_{i:04d}.txt"
                            manager._safe_write(chunk_file, sc.content)
                            paths.append(str(chunk_file))

                            chunk_infos.append(
                                ChunkInfo(
                                    chunk_id=sc.chunk_id or f"chunk_{i:04d}",
                                    file_path=str(chunk_file),
                                    start_offset=0,  # Semantic chunks don't use offsets
                                    end_offset=len(sc.content),
                                    size=len(sc.content),
                                )
                            )

                        # Update state
                        if manager.state:
                            manager.state.chunks = chunk_infos
                            manager.state.phase = "chunking"
                            manager.state.config.chunk_size = size
                            manager.state.config.chunk_overlap = 0
                            manager.save()

                        print(f"[CHUNK] Created {len(paths)} semantic chunks")
                        return paths

                except Exception as e:
                    print(f"[WARN] Semantic chunking failed, falling back to character-based: {e}")

        # Fallback: Character-based chunking (original behavior)
        # chunk_indices() now validates parameters, so this will raise if invalid
        content = manager.get_context()
        spans = chunk_indices(size, overlap)

        # Issue #2 FIX: Chunk count safety circuit breaker
        chunk_count = len(spans)
        if chunk_count > MAX_ABSOLUTE_CHUNKS:
            raise ValueError(
                f"Chunk count ({chunk_count}) exceeds safety limit ({MAX_ABSOLUTE_CHUNKS}). "
                f"This would require {chunk_count} API calls. "
                f"Use --lazy mode or --target to reduce analysis scope, "
                f"or increase chunk size (current: {size})."
            )
        if chunk_count > MAX_RECOMMENDED_CHUNKS:
            import sys
            print(
                f"[WARN] High chunk count detected: {chunk_count} chunks.\n"
                f"       This will require {chunk_count} API calls.\n"
                f"       Consider using --lazy mode or --target to reduce scope.\n"
                f"       Or increase chunk size (current: {size}).",
                file=sys.stderr,
            )

        for i, (start, end) in enumerate(spans):
            chunk_file = out_path / f"chunk_{i:04d}.txt"
            chunk_content = content[start:end]
            manager._safe_write(chunk_file, chunk_content)
            paths.append(str(chunk_file))

            chunk_infos.append(
                ChunkInfo(
                    chunk_id=f"chunk_{i:04d}",
                    file_path=str(chunk_file),
                    start_offset=start,
                    end_offset=end,
                    size=len(chunk_content),
                )
            )

        # Update state
        if manager.state:
            manager.state.chunks = chunk_infos
            manager.state.phase = "chunking"
            manager.state.config.chunk_size = size
            manager.state.config.chunk_overlap = overlap
            manager.save()

        return paths

    def get_status() -> dict[str, Any]:
        """Get current state summary."""
        if not manager.state:
            return {"status": "not_initialized"}

        return {
            "session_id": manager.state.session_id,
            "phase": manager.state.phase,
            "context_size": (
                manager.state.context_meta.total_size if manager.state.context_meta else 0
            ),
            "total_chunks": len(manager.state.chunks),
            "progress_percent": manager.state.progress_percent,
        }

    # FIX-FR-017: Add missing buffer manipulation functions
    def add_buffer(text: str) -> None:
        """Add text to result buffer."""
        if manager.state:
            manager.state.buffers.append(str(text))
            manager.save()

    def get_buffers() -> list[str]:
        """Get all buffer contents."""
        if manager.state:
            return manager.state.buffers
        return []

    def clear_buffers() -> None:
        """Clear all buffers."""
        if manager.state:
            manager.state.buffers = []
            manager.save()

    def add_result(result: dict) -> None:
        """Add a chunk result and update progress."""
        if manager.state:
            chunk_result = ChunkResult.model_validate(result)
            manager.state.results.append(chunk_result)

            # FIX-FR-010: Calculate progress_percent
            total = len(manager.state.chunks)
            completed = len(manager.state.results)
            manager.state.progress_percent = (completed / total * 100) if total > 0 else 0

            manager.save()

    def add_results_from_file(file_path: str) -> dict:
        """D6-FIX: Add multiple chunk results from a JSON file.

        Supports two formats:
        1. Array of results: [{"chunk_id": "...", ...}, ...]
        2. Single result object: {"chunk_id": "...", ...}

        Issue 4 FIX: Added OSError handling, path traversal protection, file size limit.

        Args:
            file_path: Path to JSON file containing results.

        Returns:
            Dict with 'added' count and any 'errors'.
        """
        import json
        from pathlib import Path

        # Issue 4 FIX: File size limit (10MB)
        MAX_IMPORT_SIZE = 10 * 1024 * 1024

        result_path = Path(file_path)
        if not result_path.exists():
            return {"added": 0, "errors": [f"File not found: {file_path}"]}

        # Issue 4 FIX: Path traversal protection
        # Allow files within context directory or session directory
        try:
            resolved = result_path.resolve()
            allowed_roots = []

            # Add context root if available
            if manager.state and manager.state.context_meta:
                context_root = Path(manager.state.context_meta.path).resolve()
                if context_root.is_dir():
                    allowed_roots.append(context_root)
                else:
                    allowed_roots.append(context_root.parent)

            # Add session directory
            allowed_roots.append(manager.state_dir.resolve())

            # Check if file is within allowed directories
            # Security FIX: Use relative_to instead of startswith to prevent
            # path traversal attacks (e.g., /alice matching /alice_secrets)
            is_allowed = False
            for root in allowed_roots:
                try:
                    resolved.relative_to(root)
                    is_allowed = True
                    break
                except ValueError:
                    continue
            if not is_allowed:
                return {
                    "added": 0,
                    "errors": [
                        f"Path security: file must be within context or session directory"
                    ],
                }
        except (OSError, ValueError) as e:
            return {"added": 0, "errors": [f"Path validation failed: {e}"]}

        # Issue 4 FIX: File size check
        try:
            file_size = result_path.stat().st_size
            if file_size > MAX_IMPORT_SIZE:
                return {
                    "added": 0,
                    "errors": [
                        f"File too large: {file_size:,} bytes (max {MAX_IMPORT_SIZE:,})"
                    ],
                }
        except OSError as e:
            return {"added": 0, "errors": [f"Cannot stat file: {e}"]}

        # Issue 4 FIX: Handle OSError (PermissionError, etc.)
        try:
            with open(result_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return {"added": 0, "errors": [f"Invalid JSON: {e}"]}
        except OSError as e:
            return {"added": 0, "errors": [f"Cannot read file: {e}"]}

        # Normalize to list
        if isinstance(data, dict):
            data = [data]

        added = 0
        errors = []
        for i, result in enumerate(data):
            try:
                add_result(result)
                added += 1
            except Exception as e:
                errors.append(f"Result {i}: {e}")

        return {"added": added, "errors": errors if errors else None}

    def set_phase(phase: str) -> None:
        """Update current phase."""
        if manager.state:
            manager.state.phase = phase
            manager.save()

    def set_final_answer(answer: str) -> None:
        """Set the final answer."""
        if manager.state:
            manager.state.final_answer = answer
            manager.state.phase = "completed"
            manager.state.progress_percent = 100.0
            manager.save()

    # =========================================================================
    # Phase 3: Lazy Mode Helpers
    # =========================================================================

    def is_lazy_mode() -> bool:
        """Check if currently in lazy mode.

        Returns:
            True if lazy mode is active, False otherwise.
        """
        if not manager.state or not manager.state.config:
            return False
        return manager.state.config.scan_mode == ScanMode.LAZY

    def get_tree_view() -> str:
        """Get the directory tree view (for lazy mode).

        Returns:
            Tree view string showing directory structure.
            In full mode, generates tree view on-demand.
        """
        # Issue 3 FIX: Use public property instead of private attribute access
        if manager.lazy_tree_view:
            return manager.lazy_tree_view

        # Full mode: generate tree on demand
        if manager.state and manager.state.context_meta:
            from pathlib import Path

            context_path = Path(manager.state.context_meta.path)
            if context_path.is_dir():
                return generate_tree_view(
                    context_path,
                    max_depth=manager.state.config.lazy_depth,
                    max_files=manager.state.config.lazy_file_limit,
                    should_prune=default_should_prune,
                )
            else:
                return f"{context_path.name} ({context_path.stat().st_size} bytes)"

        return "No context loaded"

    def preview_dir(subpath: str, max_depth: int = 2, max_files: int = 30) -> str:
        """Preview a subdirectory's structure (read-only, no state change).

        Args:
            subpath: Relative path within the context to preview.
            max_depth: Maximum depth to traverse (default: 2).
            max_files: Maximum files to show (default: 30).

        Returns:
            Tree view of the subdirectory.
        """
        if not manager.state or not manager.state.context_meta:
            return "No context loaded"

        from pathlib import Path

        context_path = Path(manager.state.context_meta.path)
        target_path = context_path / subpath

        if not target_path.exists():
            return f"Path not found: {subpath}"

        if not target_path.is_dir():
            # Show file info instead
            try:
                size = target_path.stat().st_size
                return f"File: {subpath} ({size} bytes)"
            except OSError as e:
                return f"Cannot access: {subpath} ({e})"

        # Validate path is within context (security)
        try:
            target_path.resolve().relative_to(context_path.resolve())
        except ValueError:
            return f"Path outside context: {subpath}"

        return generate_tree_view(
            target_path,
            max_depth=max_depth,
            max_files=max_files,
            should_prune=default_should_prune,
        )

    def load_file(filepath: str) -> str:
        """Load a specific file's content (for lazy mode exploration).

        In lazy mode, this is how you access file contents on-demand.
        In full mode, this reads the file from disk (not from cached context).

        Args:
            filepath: Relative path within the context to load.

        Returns:
            File contents as string, or error message.
        """
        if not manager.state or not manager.state.context_meta:
            return "No context loaded"

        from pathlib import Path

        context_path = Path(manager.state.context_meta.path)
        target_path = context_path / filepath

        if not target_path.exists():
            return f"File not found: {filepath}"

        if not target_path.is_file():
            return f"Not a file: {filepath}"

        # Validate path is within context (security)
        try:
            target_path.resolve().relative_to(context_path.resolve())
        except ValueError:
            return f"Path outside context: {filepath}"

        # Size check
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
        file_size = target_path.stat().st_size
        if file_size > MAX_FILE_SIZE:
            return f"File too large: {filepath} ({file_size} bytes, max {MAX_FILE_SIZE})"

        # Issue 3 FIX: Binary file detection (null bytes check)
        try:
            with open(target_path, "rb") as f:
                chunk = f.read(8192)
                if b"\x00" in chunk:
                    return f"[BINARY FILE] Cannot display binary content: {filepath}"
        except Exception:
            pass  # Fall through to text read attempt

        try:
            content = target_path.read_text(encoding="utf-8", errors="replace")
            return truncate_output(content, MAX_CONTEXT_PREVIEW)
        except Exception as e:
            return f"Error reading file: {e}"

    def grep_file(
        pattern: str, filepath: str, max_matches: int = 20, window: int = 100
    ) -> list[dict]:
        """Search a specific file with regex (works in lazy mode).

        Issue 4 FIX: Provides file-specific search capability for lazy mode
        where global grep() is not available.

        Args:
            pattern: Regex pattern to search for.
            filepath: Relative path within the context to search.
            max_matches: Maximum number of results to return.
            window: Characters of context around each match.

        Returns:
            List of match dictionaries with match, span, snippet.
            Returns [{"error": "..."}] if file cannot be loaded.

        Raises:
            ValueError: If pattern is detected as potentially dangerous ReDoS.
            TimeoutError: If regex execution times out.

        Example:
            >>> grep_file("def main", "src/app.py")
            [{"match": "def main()", "span": [120, 130], "snippet": "..."}]
        """
        # Load file content using existing load_file helper
        content = load_file(filepath)

        # Check for error responses from load_file
        if content.startswith("[BINARY FILE]"):
            return [{"error": "BINARY_FILE", "message": content}]
        if content.startswith("File not found:"):
            return [{"error": "FILE_NOT_FOUND", "message": content}]
        if content.startswith("Not a file:"):
            return [{"error": "NOT_A_FILE", "message": content}]
        if content.startswith("Path outside context:"):
            return [{"error": "PATH_SECURITY", "message": content}]
        if content.startswith("File too large:"):
            return [{"error": "FILE_TOO_LARGE", "message": content}]
        if content.startswith("Error reading file:"):
            return [{"error": "READ_ERROR", "message": content}]
        if content.startswith("No context loaded"):
            return [{"error": "NO_CONTEXT", "message": content}]

        # Perform the actual grep on file content
        return safe_grep(pattern, content, max_matches, window)

    helpers = {
        "peek": peek,
        "peek_head": peek_head,
        "peek_tail": peek_tail,
        "grep": grep,
        "grep_file": grep_file,  # Issue 4 FIX: File-specific grep for lazy mode
        "chunk_indices": chunk_indices,
        "write_chunks": write_chunks,
        "add_buffer": add_buffer,  # FIX-FR-017
        "get_buffers": get_buffers,  # FIX-FR-017
        "clear_buffers": clear_buffers,  # FIX-FR-017
        "add_result": add_result,  # FIX-FR-010
        "add_results_from_file": add_results_from_file,  # D6-FIX: Batch import
        "set_phase": set_phase,
        "set_final_answer": set_final_answer,
        "get_status": get_status,
        "context_length": lambda: len(manager.get_context()),
        # Phase 3: Lazy Mode helpers
        "is_lazy_mode": is_lazy_mode,
        "get_tree_view": get_tree_view,
        "preview_dir": preview_dir,
        "load_file": load_file,
        # FIX-CVE-2026-002: REMOVED "re": re - Prevents ReDoS attacks
        # Users should use grep() function instead of raw regex
    }

    # HELPER_DETECTION_FIX: Validate that helpers match HELPER_NAMES constant
    # This catches desynchronization bugs at runtime
    actual_keys = frozenset(helpers.keys())
    if actual_keys != HELPER_NAMES:
        missing = HELPER_NAMES - actual_keys
        extra = actual_keys - HELPER_NAMES
        warnings.warn(
            f"HELPER_NAMES constant desync! "
            f"Missing: {missing or 'none'}, Extra: {extra or 'none'}. "
            f"Update HELPER_NAMES at module level to match.",
            RuntimeWarning,
            stacklevel=2,
        )

    return helpers
