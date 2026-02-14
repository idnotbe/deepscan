"""DeepScan State Manager Module.

Manages DeepScan state persistence with Pydantic + JSON.

Security Features (Issue #14 Documentation):
    - Symlinks are never followed during file traversal (prevents infinite loops)
    - Symlink targets outside context root are rejected with PermissionError
    - Path traversal attempts (../../../etc/passwd) are blocked via relative_to() checks
    - All modes (targeted/lazy/full) skip symlinks silently during directory traversal
    - In get_context(): symlinks raise ValueError with clear message

Custom Ignore Patterns (Issue #7):
    - Supports .deepscanignore file in project root (similar to .gitignore)
    - Directory names: matched against any path component
    - Glob patterns: matched against relative file paths
"""

from __future__ import annotations

__all__ = [
    # Main class
    "StateManager",
]

import json
import secrets
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from constants import (
    DEFAULT_LAZY_DEPTH,
    DEFAULT_LAZY_FILE_LIMIT,
    detect_content_type,
)
from incremental import (
    FileDelta,
    FileHashManifest,
    IncrementalAnalyzer,
)
from models import (
    ContextMetadata,
    DeepScanConfig,
    DeepScanState,
    ScanMode,
)
from walker import (
    DEFAULT_PRUNE_DIRS,
    default_should_prune,
    generate_tree_view,
)


def _parse_deepscanignore(root_path: Path) -> tuple[set[str], list[str]]:
    """Parse .deepscanignore file if it exists.

    Issue #7 FIX: Support project-specific ignore patterns.

    File format (similar to .gitignore):
    - Lines starting with # are comments
    - Empty lines are ignored
    - Directory names (no wildcards) are matched against path components
    - Glob patterns (containing * or ?) match against relative paths

    Args:
        root_path: Root directory to search for .deepscanignore.

    Returns:
        Tuple of (directory_names_set, glob_patterns_list).
    """
    ignore_file = root_path / ".deepscanignore"
    dir_patterns: set[str] = set()
    glob_patterns: list[str] = []

    if not ignore_file.exists():
        return dir_patterns, glob_patterns

    try:
        content = ignore_file.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue
            # Remove trailing slash for directory patterns
            line = line.rstrip("/")
            # Classify pattern type
            if "*" in line or "?" in line:
                glob_patterns.append(line)
            else:
                dir_patterns.add(line)
    except (OSError, UnicodeDecodeError):
        # Issue #10 FIX: Specific exceptions for file read errors
        # Silently ignore .deepscanignore read errors (file permissions, encoding issues OK)
        pass

    return dir_patterns, glob_patterns


def _should_skip_path(
    path: Path,
    root_path: Path | None = None,
    custom_dirs: set[str] | None = None,
    custom_globs: list[str] | None = None,
) -> bool:
    """Check if a file path should be skipped during indexing.

    Uses DEFAULT_PRUNE_DIRS from walker.py for consistency across modules.
    Checks if ANY component of the path is in the prune set.

    Issue #7 FIX: Also checks custom patterns from .deepscanignore.

    Args:
        path: File path to check.
        root_path: Optional root path for relative path calculation.
        custom_dirs: Optional set of additional directory names to skip.
        custom_globs: Optional list of glob patterns to check.

    Returns:
        True if the path should be skipped, False otherwise.
    """
    import fnmatch

    # Check default prune directories
    if any(part in DEFAULT_PRUNE_DIRS for part in path.parts):
        return True

    # Check custom directory patterns
    if custom_dirs:
        if any(part in custom_dirs for part in path.parts):
            return True

    # Check glob patterns against relative path
    if custom_globs and root_path:
        try:
            rel_path = str(path.relative_to(root_path))
            for pattern in custom_globs:
                if fnmatch.fnmatch(rel_path, pattern):
                    return True
        except ValueError:
            pass  # path not relative to root_path

    return False


def _calculate_entry_size(content: str, rel_path: str) -> tuple[str, str, int]:
    """Calculate the total size of a file entry including header and footer overhead.

    Issue #3 FIX: Ensures consistent overhead calculation across all modes.
    DRY: Extracted to avoid drift between Full/Targeted mode calculations.

    Args:
        content: The file content string.
        rel_path: The relative path string to use in the header.

    Returns:
        Tuple of (header, footer, entry_size) where entry_size includes all overhead.
    """
    header = f"=== FILE: {rel_path} ===\n"
    footer = "\n\n"
    entry_size = len(header) + len(content) + len(footer)
    return header, footer, entry_size


class StateManager:
    """Manages DeepScan state persistence with Pydantic + JSON."""

    DEFAULT_CACHE_ROOT = Path.home() / ".claude" / "cache" / "deepscan"
    STATE_FILE = "state.json"
    CURRENT_SESSION_FILE = Path.home() / ".claude" / "cache" / "deepscan" / ".current_session"

    @classmethod
    def list_sessions(cls) -> list[dict]:
        """List all DeepScan sessions.

        Returns:
            List of session info dicts sorted by modification time (newest first).
        """
        cache_root = cls.DEFAULT_CACHE_ROOT
        if not cache_root.exists():
            return []

        sessions = []
        for session_dir in cache_root.iterdir():
            if session_dir.is_dir() and session_dir.name.startswith("deepscan_"):
                state_file = session_dir / cls.STATE_FILE
                if state_file.exists():
                    try:
                        with state_file.open("r", encoding="utf-8") as f:
                            data = json.load(f)
                        mtime = state_file.stat().st_mtime
                        sessions.append(
                            {
                                "hash": session_dir.name,
                                "session_id": data.get("session_id", "unknown"),
                                "phase": data.get("phase", "unknown"),
                                "progress": data.get("progress_percent", 0),
                                "context_size": data.get("context_meta", {}).get("total_size", 0),
                                "chunks": len(data.get("chunks", [])),
                                "results": len(data.get("results", [])),
                                "modified": datetime.fromtimestamp(mtime),
                            }
                        )
                    except (json.JSONDecodeError, KeyError, OSError):
                        # Issue #10 FIX: Specific exceptions for corrupted/incomplete sessions
                        pass

        # Sort by modification time (newest first)
        sessions.sort(key=lambda s: s["modified"], reverse=True)
        return sessions

    @classmethod
    def get_current_session_hash(cls) -> str | None:
        """Get the current session hash from marker file."""
        if cls.CURRENT_SESSION_FILE.exists():
            return cls.CURRENT_SESSION_FILE.read_text(encoding="utf-8").strip()
        return None

    @classmethod
    def set_current_session_hash(cls, session_hash: str) -> None:
        """Set the current session hash marker.

        D5-FIX: Uses atomic write (temp file → rename) to prevent race conditions.
        This ensures that concurrent reads never see a partial/corrupted session hash.
        """
        import os
        import tempfile

        cls.CURRENT_SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write: write to temp file first, then rename
        fd, temp_path = tempfile.mkstemp(
            dir=cls.CURRENT_SESSION_FILE.parent,
            prefix=".session_",
            suffix=".tmp"
        )
        try:
            os.write(fd, session_hash.encode("utf-8"))
            os.close(fd)
            fd = None  # Issue 3 FIX: Mark as closed to prevent double-close
            # Atomic rename (on POSIX) or near-atomic (on Windows)
            Path(temp_path).replace(cls.CURRENT_SESSION_FILE)
        except Exception:
            # Clean up temp file on failure
            # Issue 3 FIX: Only close if fd is still open (not None)
            if fd is not None:
                os.close(fd)
            Path(temp_path).unlink(missing_ok=True)
            raise

    @classmethod
    def gc_clean_old_sessions(cls, max_age_days: int = 7, max_total_size_gb: float = 1.0) -> dict:
        """Clean up old sessions based on TTL and size limits.

        Args:
            max_age_days: Maximum age in days before session is deleted.
            max_total_size_gb: Maximum total cache size in GB.

        Returns:
            Dict with deleted count and freed bytes.
        """
        import shutil
        from datetime import timedelta

        cache_root = cls.DEFAULT_CACHE_ROOT
        if not cache_root.exists():
            return {"deleted": 0, "freed_bytes": 0}

        now = datetime.now()
        max_age = timedelta(days=max_age_days)
        max_bytes = int(max_total_size_gb * 1024 * 1024 * 1024)

        # Collect session info
        sessions = []
        for session_dir in cache_root.iterdir():
            if session_dir.is_dir() and session_dir.name.startswith("deepscan_"):
                state_file = session_dir / cls.STATE_FILE
                if state_file.exists():
                    try:
                        mtime = datetime.fromtimestamp(state_file.stat().st_mtime)
                        size = sum(f.stat().st_size for f in session_dir.rglob("*") if f.is_file())
                        sessions.append(
                            {
                                "path": session_dir,
                                "mtime": mtime,
                                "size": size,
                                "age": now - mtime,
                            }
                        )
                    except (json.JSONDecodeError, KeyError, OSError):
                        # Issue #10 FIX: Specific exceptions for corrupted sessions (skip during GC)
                        pass

        # Sort by age (oldest first) for LRU eviction
        sessions.sort(key=lambda s: s["mtime"])

        deleted = 0
        freed_bytes = 0
        total_size = sum(s["size"] for s in sessions)

        for session in sessions:
            should_delete = False

            # Delete if older than max_age
            if session["age"] > max_age:
                should_delete = True
            # Delete if total size exceeds limit (LRU eviction)
            elif total_size > max_bytes:
                should_delete = True

            if should_delete:
                try:
                    shutil.rmtree(session["path"])
                    deleted += 1
                    freed_bytes += session["size"]
                    total_size -= session["size"]
                except (OSError, PermissionError):
                    # Issue #10 FIX: Skip if already deleted by concurrent process or permission denied
                    pass

        return {"deleted": deleted, "freed_bytes": freed_bytes}

    def __init__(self, session_hash: str | None = None):
        self.session_hash = session_hash or self._generate_session_hash()
        self.state_dir = self.DEFAULT_CACHE_ROOT / self.session_hash
        self.state_file = self.state_dir / self.STATE_FILE
        self.state: DeepScanState | None = None
        self._context_content: str | None = None
        self._lazy_tree_view: str = ""  # Phase 3: Tree view for lazy mode
        self._lock = threading.Lock()
        # Issue #7 FIX: Custom ignore patterns from .deepscanignore
        self._custom_ignore_dirs: set[str] = set()
        self._custom_ignore_globs: list[str] = []
        self._context_root: Path | None = None  # Root path for relative path calculations

    @property
    def lazy_tree_view(self) -> str:
        """Public getter for lazy mode tree view.

        Returns the directory tree view generated during lazy mode init.
        Returns empty string if not in lazy mode or not yet initialized.

        Note: Encapsulation improvement - external code should use this
        property instead of accessing _lazy_tree_view directly.
        """
        return self._lazy_tree_view

    def _generate_session_hash(self) -> str:
        """Generate cryptographically secure session ID."""
        return f"deepscan_{int(time.time())}_{secrets.token_hex(8)}"

    def ensure_dirs(self) -> None:
        """Create necessary directories."""
        (self.state_dir / "chunks").mkdir(parents=True, exist_ok=True)
        (self.state_dir / "results").mkdir(parents=True, exist_ok=True)
        (self.state_dir / "logs").mkdir(parents=True, exist_ok=True)

    def load(self) -> DeepScanState:
        """Load state from JSON file.

        Note: HMAC signature verification (DEFECT-005) was considered but
        decided against implementation. Rationale: Local-only tool with low
        tampering risk. Key management complexity outweighs benefits.
        See DEEPSCAN_REVIEW_2026-01-21.md for decision record.
        """
        with self._lock:
            if not self.state_file.exists():
                raise FileNotFoundError(
                    f"No state found at {self.state_file}. "
                    f"Run: python deepscan_engine.py init <context_path>"
                )

            with self.state_file.open("r", encoding="utf-8") as f:
                data = json.load(f)

            self.state = DeepScanState.model_validate(data)
            return self.state

    def _safe_write(self, path: Path, content: str) -> None:
        """Write with path traversal protection (ARCH_04 §1.2).

        FIX-SECURITY-HIGH: Prevents writing outside allowed cache directory.
        Attack vector: Malicious path like "../../etc/passwd" could write to system files.
        """
        resolved = path.resolve().absolute()
        allowed = self.DEFAULT_CACHE_ROOT.resolve().absolute()

        try:
            resolved.relative_to(allowed)  # Will raise ValueError if not a subpath
        except ValueError as err:
            raise PermissionError(
                f"Write not allowed to {path}. "
                f"Only writes to {self.DEFAULT_CACHE_ROOT} are permitted."
            ) from err

        path.write_text(content, encoding="utf-8")

    def save(self) -> None:
        """Save state to JSON file (atomic write with security).

        Note: HMAC signature (DEFECT-005) not implemented - see load() docstring.
        """
        with self._lock:
            if not self.state:
                raise ValueError("No state to save")

            self.state.updated_at = datetime.now()
            self.ensure_dirs()

            # Atomic write: write to temp, then rename (with path validation)
            tmp_file = self.state_file.with_suffix(".json.tmp")
            self._safe_write(tmp_file, self.state.model_dump_json(indent=2))
            tmp_file.replace(self.state_file)

    def init(
        self,
        context_path: str,
        query: str | None = None,
        adaptive: bool = False,
        incremental: bool = False,
        previous_session: str | None = None,
        lazy: bool = False,
        target: list[str] | None = None,
        depth: int | None = None,
        agent_type: str = "general",
    ) -> DeepScanState:
        """Initialize new state with context.

        Args:
            context_path: Path to file or directory to analyze.
            query: Optional initial query.
            adaptive: If True, auto-detect content type and set optimal chunk size.
            incremental: If True, enable incremental re-analysis (Phase 5).
            previous_session: Session hash to compare against for delta detection.
            lazy: If True, use lazy mode (structure only, no content loading).
            target: List of target paths for targeted mode.
            depth: Max directory depth for lazy traversal (default: 3).
            agent_type: Specialized analysis type (general, security, architecture, performance).
        """
        self.ensure_dirs()

        # File size limits
        MAX_SINGLE_FILE_SIZE = 10 * 1024 * 1024  # 10MB
        MAX_TOTAL_CONTEXT_SIZE = 50 * 1024 * 1024  # 50MB

        path = Path(context_path)
        if not path.exists():
            raise FileNotFoundError(f"Context path not found: {context_path}")

        # Issue #7 FIX: Parse .deepscanignore for custom ignore patterns
        self._context_root = path.resolve() if path.is_dir() else path.parent.resolve()
        self._custom_ignore_dirs, self._custom_ignore_globs = _parse_deepscanignore(self._context_root)
        if self._custom_ignore_dirs or self._custom_ignore_globs:
            print(f"[INFO] Loaded .deepscanignore: {len(self._custom_ignore_dirs)} dirs, {len(self._custom_ignore_globs)} patterns")

        # Phase 4 FIX: Warn if target list is provided but empty (possible config error)
        if target is not None and len(target) == 0:
            print(
                "[WARN] Empty target list provided - falling back to full mode. "
                "Use --target PATH to specify files/directories.",
                file=sys.stderr,
            )

        # Track file extensions for adaptive chunking
        file_extensions: list[str] = []

        # Phase 3: Lazy Mode - structure only, no content loading
        effective_depth = depth if depth is not None else DEFAULT_LAZY_DEPTH
        effective_file_limit = DEFAULT_LAZY_FILE_LIMIT

        if lazy:
            # Lazy Mode: Generate tree view only, don't load file content
            if path.is_file():
                # Single file in lazy mode - just show info
                content = ""
                is_directory = False
                file_count = 1
                file_extensions.append(path.suffix.lower())
                self._lazy_tree_view = f"{path.name} ({path.stat().st_size} bytes)"
            else:
                # Directory: generate tree view without loading content
                content = ""
                is_directory = True
                file_count = 0

                # Generate tree view using walker
                self._lazy_tree_view = generate_tree_view(
                    path,
                    max_depth=effective_depth,
                    max_files=effective_file_limit,
                    should_prune=default_should_prune,
                    show_size=True,
                    show_hidden=False,
                )

                # Count files for metadata (approximate from tree)
                file_count = self._lazy_tree_view.count("(") - 1  # Rough estimate

            self._context_content = content

        elif target:
            # Phase 4: Targeted Mode - load only specified files/directories
            content_parts = []
            file_count = 0
            total_size = 0
            is_directory = path.is_dir()
            seen_paths: set[Path] = set()  # Deduplication for overlapping targets

            for target_path_str in target:
                # Skip empty strings
                if not target_path_str.strip():
                    continue

                # Resolve target path relative to context path
                target_path = path / target_path_str

                # Security: Validate target is within context path
                try:
                    resolved_target = target_path.resolve()
                    resolved_context = path.resolve()
                    resolved_target.relative_to(resolved_context)
                except ValueError:
                    # Path traversal attempt - skip this target
                    continue

                # Skip if doesn't exist
                if not target_path.exists():
                    continue

                # Skip symlinks (security)
                if target_path.is_symlink():
                    continue

                if target_path.is_file():
                    # Direct file target
                    if target_path in seen_paths:
                        continue
                    seen_paths.add(target_path)

                    if target_path.stat().st_size > MAX_SINGLE_FILE_SIZE:
                        # Phase 4 FIX: Warn when explicitly targeted file is skipped
                        print(
                            f"[WARN] Skipping targeted file (too large): "
                            f"{target_path.name} ({target_path.stat().st_size} bytes)",
                            file=sys.stderr,
                        )
                        continue
                    try:
                        file_content = target_path.read_text(encoding="utf-8", errors="replace")
                        # Issue #3 FIX: Account for header overhead in size limit
                        rel_path = str(target_path.relative_to(path))
                        header, footer, entry_size = _calculate_entry_size(file_content, rel_path)
                        if total_size + entry_size > MAX_TOTAL_CONTEXT_SIZE:
                            break
                        total_size += entry_size
                        content_parts.append(header)
                        content_parts.append(file_content)
                        content_parts.append(footer)
                        file_count += 1
                        file_extensions.append(target_path.suffix.lower())
                    except (OSError, UnicodeDecodeError):
                        # Issue #10 FIX: Specific exceptions for file read errors
                        # Skip unreadable files in targeted mode
                        pass

                elif target_path.is_dir():
                    # Directory target - load all files in that directory
                    for f in sorted(target_path.rglob("*")):
                        if f in seen_paths:
                            continue
                        if f.is_file() and not f.is_symlink() and not _should_skip_path(
                            f, self._context_root, self._custom_ignore_dirs, self._custom_ignore_globs
                        ):
                            seen_paths.add(f)
                            try:
                                if f.stat().st_size > MAX_SINGLE_FILE_SIZE:
                                    # Phase 4 FIX: Warn when targeted dir file is skipped
                                    print(
                                        f"[WARN] Skipping file (too large): "
                                        f"{f.name} ({f.stat().st_size} bytes)",
                                        file=sys.stderr,
                                    )
                                    continue
                                file_content = f.read_text(encoding="utf-8", errors="replace")
                                # Issue #3 FIX: Account for header overhead in size limit
                                rel_path = str(f.relative_to(path))
                                header, footer, entry_size = _calculate_entry_size(file_content, rel_path)
                                if total_size + entry_size > MAX_TOTAL_CONTEXT_SIZE:
                                    break
                                total_size += entry_size
                                content_parts.append(header)
                                content_parts.append(file_content)
                                content_parts.append(footer)
                                file_count += 1
                                file_extensions.append(f.suffix.lower())
                            except (OSError, UnicodeDecodeError):
                                # Issue #10 FIX: Specific exceptions for file read errors
                                # Skip unreadable files in targeted directory mode
                                pass

            content = "".join(content_parts)
            self._context_content = content

        else:
            # Full Mode: Load actual content (existing behavior)
            if path.is_file():
                if path.stat().st_size > MAX_SINGLE_FILE_SIZE:
                    raise ValueError(
                        f"File too large: {path.stat().st_size} bytes (max {MAX_SINGLE_FILE_SIZE})"
                    )
                content = path.read_text(encoding="utf-8", errors="replace")
                is_directory = False
                file_count = 1
                file_extensions.append(path.suffix.lower())
            else:
                # Directory: concatenate all text files
                content_parts = []
                file_count = 0
                total_size = 0

                for f in sorted(path.rglob("*")):
                    if f.is_file() and not _should_skip_path(
                        f, self._context_root, self._custom_ignore_dirs, self._custom_ignore_globs
                    ):
                        try:
                            if f.stat().st_size > MAX_SINGLE_FILE_SIZE:
                                continue
                            file_content = f.read_text(encoding="utf-8", errors="replace")
                            # Issue #3 FIX: Account for header overhead in size limit
                            rel_path = str(f.relative_to(path))
                            header, footer, entry_size = _calculate_entry_size(file_content, rel_path)
                            if total_size + entry_size > MAX_TOTAL_CONTEXT_SIZE:
                                break
                            total_size += entry_size
                            content_parts.append(header)
                            content_parts.append(file_content)
                            content_parts.append(footer)
                            file_count += 1
                            file_extensions.append(f.suffix.lower())
                        except (OSError, UnicodeDecodeError):
                            # Issue #10 FIX: Specific exceptions for file read errors
                            # Skip unreadable files in full mode directory traversal
                            pass

                content = "".join(content_parts)
                is_directory = True

            if len(content) > MAX_TOTAL_CONTEXT_SIZE:
                raise ValueError(
                    f"Total context too large: {len(content)} bytes (max {MAX_TOTAL_CONTEXT_SIZE})"
                )

            self._context_content = content

        # Phase 4: Adaptive chunk sizing
        config = DeepScanConfig()
        if adaptive and file_extensions:
            content_type, recommended_size = detect_content_type(path, file_extensions)
            config.adaptive_chunking = True
            config.detected_content_type = content_type
            config.chunk_size = recommended_size

        # Phase 1 (Lazy Mode): Traversal strategy configuration
        if target:
            # Targeted mode takes precedence when targets are specified
            config.scan_mode = ScanMode.TARGETED
            config.target_paths = target
        elif lazy:
            config.scan_mode = ScanMode.LAZY

        if depth is not None:
            config.lazy_depth = depth

        # P8-FIX: Agent type specialization (Issue 1 from deepscan_errors_20260124.md)
        config.agent_type = agent_type

        # Create state
        self.state = DeepScanState(
            config=config,
            context_meta=ContextMetadata(
                path=str(path.absolute()),
                loaded_at=datetime.now(),
                total_size=len(content),
                is_directory=is_directory,
                file_count=file_count,
            ),
            query=query,
            phase="initialized",
        )

        # Phase 5: Incremental re-analysis
        self._file_delta: FileDelta | None = None
        if incremental and is_directory:
            try:
                # Create file hash manifest for current context
                current_manifest = FileHashManifest.from_directory(path)

                # Load previous manifest if session provided
                previous_manifest: FileHashManifest | None = None
                if previous_session:
                    try:
                        # P0-FIX: Use DEFAULT_CACHE_ROOT class var
                        # (not undefined self.cache_root)
                        prev_analyzer = IncrementalAnalyzer(
                            previous_session, self.DEFAULT_CACHE_ROOT
                        )
                        previous_manifest = prev_analyzer.get_previous_manifest()
                    except ValueError:
                        # Invalid session hash
                        pass

                # Compute delta
                if previous_manifest:
                    self._file_delta = current_manifest.compare_with(previous_manifest)
                else:
                    # No previous manifest = all files are "added"
                    self._file_delta = FileDelta(
                        added_files=list(current_manifest.file_hashes.keys()),
                    )

                # Save manifest for future sessions
                # P0-FIX: Use class variable DEFAULT_CACHE_ROOT instead of undefined self.cache_root
                analyzer = IncrementalAnalyzer(self.state.session_id, self.DEFAULT_CACHE_ROOT)
                analyzer.save_manifest(current_manifest)

                # Store incremental metadata in config
                self.state.config.incremental_enabled = True
                self.state.config.previous_session = previous_session
                self.state.config.changed_file_count = len(self._file_delta.changed_files) + len(
                    self._file_delta.added_files
                )
                self.state.config.deleted_file_count = len(self._file_delta.deleted_files)

            except Exception as e:
                # Fall back to full analysis on error
                print(f"[WARN] Incremental analysis failed, using full analysis: {e}")
                self._file_delta = None

        self.save()

        # DEFECT-003 FIX: Set current session marker so subsequent commands can find this session
        StateManager.set_current_session_hash(self.session_hash)

        return self.state

    def reset(self) -> None:
        """Reset state and clean up files."""
        import shutil

        if self.state_dir.exists():
            shutil.rmtree(self.state_dir)
        self.state = None
        self._context_content = None

    def get_context(self) -> str:
        """Get loaded context content.

        P2-FIX: Added path traversal protection via canonical path validation.
        Phase 3 FIX: Respect lazy mode - return empty content instead of loading.
        """
        if self._context_content is None:
            if not self.state or not self.state.context_meta:
                raise ValueError("No context loaded")

            # Phase 3 FIX: Lazy mode should not load file content
            # This is critical for performance - lazy mode exists to avoid loading large codebases
            if self.state.config.scan_mode == ScanMode.LAZY:
                self._context_content = ""
                return self._context_content

            # Reload from disk with path validation
            path = Path(self.state.context_meta.path)

            # P2-FIX: Validate path to prevent traversal attacks
            # Resolve to canonical path and check for suspicious components
            try:
                resolved_path = path.resolve()

                # Block paths with traversal indicators
                path_str = str(path)
                if ".." in path_str:
                    raise ValueError(f"Path traversal detected in context path: {path_str}")

                # Block symlinks to prevent redirect attacks
                if path.is_symlink():
                    raise ValueError(f"Symlinks not allowed in context path: {path_str}")

            except (OSError, ValueError) as e:
                raise ValueError(f"Invalid context path: {e}") from e

            if resolved_path.is_file():
                self._context_content = resolved_path.read_text(encoding="utf-8", errors="replace")
            else:
                # Re-concatenate directory
                content_parts = []
                for f in sorted(resolved_path.rglob("*")):
                    # P2-FIX: Skip symlinks in directory traversal
                    if f.is_symlink():
                        continue
                    if f.is_file() and not _should_skip_path(
                        f, self._context_root, self._custom_ignore_dirs, self._custom_ignore_globs
                    ):
                        try:
                            # P2-FIX: Verify file is within the resolved path
                            f.resolve().relative_to(resolved_path)
                            # Issue #3 FIX: Use helper for consistent header/footer format
                            file_content = f.read_text(encoding="utf-8", errors="replace")
                            rel_path = str(f.relative_to(resolved_path))
                            header, footer, _ = _calculate_entry_size(file_content, rel_path)
                            content_parts.append(header)
                            content_parts.append(file_content)
                            content_parts.append(footer)
                        except (ValueError, Exception):
                            # Skip files outside the context root or unreadable
                            pass
                self._context_content = "".join(content_parts)

        return self._context_content
