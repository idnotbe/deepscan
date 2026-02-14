"""Generator-based Tree Walker for DeepScan Lazy Mode.

Phase 2 Implementation: Efficient directory traversal using os.scandir.

Key Features:
- Generator pattern for memory efficiency (yields one entry at a time)
- os.scandir for Windows performance (cached stat info in DirEntry)
- Pruning support via should_prune callback (skip directories before entering)
- Depth and file count limits
- PermissionError handling

Usage:
    from walker import tree_explore, generate_tree_view, FileEntry

    # Basic traversal
    for entry in tree_explore(Path("./src"), max_depth=3):
        print(f"{entry.path} ({entry.size} bytes)")

    # With pruning (skip node_modules, .git, etc.)
    def skip_large_dirs(path: Path) -> bool:
        return path.name in {"node_modules", ".git", "__pycache__", ".venv"}

    for entry in tree_explore(Path("./"), should_prune=skip_large_dirs):
        print(entry.path)

    # Generate tree view string
    tree_str = generate_tree_view(Path("./src"), max_depth=2, max_files=50)
    print(tree_str)

Note:
    - This is a synchronous generator. If used within an async context,
      wrap with asyncio.to_thread() or run_in_executor().
    - Symbolic links are NOT followed. Symlinks to directories appear as
      non-directories and are not recursed into. This prevents infinite loops
      from circular symlinks.
    - All datetime values are in UTC timezone for consistency.
"""

from __future__ import annotations

__all__ = [
    "FileEntry",
    "tree_explore",
    "generate_tree_view",
    "format_size",
    "default_should_prune",
    "DEFAULT_TREE_VIEW_LIMIT",
    "DEFAULT_PRUNE_DIRS",
    # Tree drawing constants
    "TREE_BRANCH",
    "TREE_LAST",
    "TREE_VERTICAL",
    "TREE_EMPTY",
]

import logging
import os
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# Module logger for debugging (disabled by default)
logger = logging.getLogger(__name__)

# Safety cap for generate_tree_view to prevent memory exhaustion
# Defined here to avoid import issues when walker.py is used standalone
# SYNC WARNING: Also defined in constants.py for consistency.
# If you change this value, update constants.py as well.
DEFAULT_TREE_VIEW_LIMIT = 10_000

# Tree drawing characters (ASCII art)
# Extracted as constants for easy customization
TREE_BRANCH = "├── "  # Non-last child connector
TREE_LAST = "└── "  # Last child connector
TREE_VERTICAL = "│   "  # Vertical continuation line
TREE_EMPTY = "    "  # Empty space (no more siblings)


@dataclass(frozen=True, slots=True)
class FileEntry:
    """Immutable entry yielded by tree_explore.

    Attributes:
        path: Absolute path to the file or directory.
        name: Base name of the file or directory.
        is_dir: True if this is a directory.
        size: File size in bytes (0 for directories).
        mtime: Last modification time in UTC (from DirEntry.stat cache).
        depth: Depth relative to start_path (0 = start_path itself).
    """

    path: Path
    name: str
    is_dir: bool
    size: int
    mtime: datetime
    depth: int

    def __repr__(self) -> str:
        """Compact representation for debugging."""
        kind = "DIR" if self.is_dir else "FILE"
        return f"FileEntry({self.name!r}, {kind}, depth={self.depth})"


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes.

    Returns:
        Formatted string like "1.2KB", "3.4MB", etc.
    """
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f}MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f}GB"


def tree_explore(
    start_path: Path | str,
    max_depth: int | None = None,
    max_files: int | None = None,
    should_prune: Callable[[Path], bool] | None = None,
    *,
    _current_depth: int = 0,
    _file_count: list[int] | None = None,
) -> Iterator[FileEntry]:
    """Lazily traverse directory tree using Generator pattern.

    Uses os.scandir for efficient traversal on Windows (cached stat info).
    Yields FileEntry objects one at a time for memory efficiency.

    Args:
        start_path: Root directory to start traversal. Accepts Path or str.
        max_depth: Maximum depth to traverse (None = unlimited).
            Must be non-negative if provided.
        max_files: Maximum entries to yield (None = unlimited).
            Must be non-negative if provided.
            Note: This counts BOTH files AND directories, not just files.
            For example, max_files=10 may yield 7 files and 3 directories.
        should_prune: Callback to skip entries BEFORE processing them.
            Returns True to skip the entry entirely (pruning).
            For directories, this also prevents entering them.
            Example: lambda p: p.name in {"node_modules", ".git"}

    Yields:
        FileEntry objects for each file and directory encountered.

    Raises:
        ValueError: If max_depth or max_files is negative.

    Note:
        - Directories are yielded BEFORE their contents.
        - Pruned entries are NOT yielded at all (filtered before sorting).
        - PermissionError and OSError are logged at DEBUG level and skipped.
        - Symbolic links are NOT followed. Symlinks to directories are treated
          as files and not recursed into, preventing infinite loops.

    Example:
        >>> for entry in tree_explore(Path("./src"), max_depth=2):
        ...     prefix = "📁" if entry.is_dir else "📄"
        ...     print(f"{prefix} {entry.path}")
    """
    # Input validation (only on initial call, not recursive)
    if _file_count is None:
        if max_depth is not None and max_depth < 0:
            raise ValueError(f"max_depth must be non-negative, got {max_depth}")
        if max_files is not None and max_files < 0:
            raise ValueError(f"max_files must be non-negative, got {max_files}")

    # Initialize file counter (mutable list for closure sharing across recursion)
    if _file_count is None:
        _file_count = [0]

    # Resolve start path (accepts both Path and str)
    start_path = Path(start_path).resolve()

    # Check depth limit
    if max_depth is not None and _current_depth > max_depth:
        return

    # Check file limit
    if max_files is not None and _file_count[0] >= max_files:
        return

    try:
        # Use os.scandir for performance (DirEntry caches stat info)
        with os.scandir(start_path) as entries:
            # OPTIMIZATION: Filter BEFORE sorting to avoid sorting pruned entries
            # This significantly improves performance in directories with many
            # ignored subdirs (e.g., node_modules with thousands of packages)
            def should_include(entry: os.DirEntry[str]) -> bool:
                if should_prune is None:
                    return True
                return not should_prune(Path(entry.path))

            # Filter first, then sort (only non-pruned entries are sorted)
            filtered_entries = (e for e in entries if should_include(e))
            sorted_entries = sorted(
                filtered_entries,
                key=lambda e: (not e.is_dir(follow_symlinks=False), e.name.lower()),
            )

            for entry in sorted_entries:
                # Check file limit before yielding
                if max_files is not None and _file_count[0] >= max_files:
                    return

                entry_path = Path(entry.path)
                is_dir = entry.is_dir(follow_symlinks=False)

                # Extract stat info from DirEntry cache (avoids extra I/O)
                try:
                    stat_info = entry.stat(follow_symlinks=False)
                    size = stat_info.st_size if not is_dir else 0
                    # Use UTC timezone for consistency across systems
                    mtime = datetime.fromtimestamp(stat_info.st_mtime, tz=timezone.utc)
                except OSError as e:
                    # Stat failed (permission, broken symlink, etc.)
                    logger.debug("Stat failed for %s: %s", entry.path, e)
                    size = 0
                    mtime = datetime.now(tz=timezone.utc)

                # Create and yield FileEntry
                file_entry = FileEntry(
                    path=entry_path,
                    name=entry.name,
                    is_dir=is_dir,
                    size=size,
                    mtime=mtime,
                    depth=_current_depth,
                )
                yield file_entry
                _file_count[0] += 1

                # Recurse into directories
                if is_dir:
                    yield from tree_explore(
                        entry_path,
                        max_depth=max_depth,
                        max_files=max_files,
                        should_prune=should_prune,
                        _current_depth=_current_depth + 1,
                        _file_count=_file_count,
                    )

    except PermissionError as e:
        # Skip directories we can't access, log for debugging
        logger.debug("Permission denied for %s: %s", start_path, e)
    except OSError as e:
        # Other OS errors (network paths, etc.) - skip with logging
        logger.debug("OS error accessing %s: %s", start_path, e)


def generate_tree_view(
    start_path: Path | str,
    max_depth: int | None = None,
    max_files: int | None = None,
    should_prune: Callable[[Path], bool] | None = None,
    show_size: bool = True,
    show_hidden: bool = False,
) -> str:
    """Generate ASCII tree view of directory structure.

    Args:
        start_path: Root directory to display. Accepts Path or str.
        max_depth: Maximum depth to traverse (None = unlimited).
            Must be non-negative if provided.
        max_files: Maximum entries to show (None = uses DEFAULT_TREE_VIEW_LIMIT).
            Must be non-negative if provided.
            Note: This counts BOTH files AND directories, not just files.
            A safety cap of 10,000 entries is applied to prevent memory issues.
        should_prune: Callback to skip directories.
        show_size: Include file sizes in output.
        show_hidden: Include hidden files (starting with '.').

    Returns:
        Formatted tree view string.

    Raises:
        ValueError: If max_depth or max_files is negative.

    Example output:
        src/
        ├── main.py (2.3KB)
        ├── auth/
        │   ├── login.py (1.1KB)
        │   └── oauth.py (0.8KB)
        └── utils/
            └── helpers.py (0.5KB)
    """
    # Apply safety cap to prevent memory exhaustion
    if max_files is None:
        effective_max_files = DEFAULT_TREE_VIEW_LIMIT
    else:
        effective_max_files = min(max_files, DEFAULT_TREE_VIEW_LIMIT)

    start_path = Path(start_path).resolve()

    # Combine hidden file filter with user's prune function
    def combined_prune(path: Path) -> bool:
        # Skip hidden files/dirs if not showing hidden
        if not show_hidden and path.name.startswith("."):
            return True
        # Apply user's prune function
        if should_prune is not None:
            return should_prune(path)
        return False

    # Collect entries with their tree structure info
    lines: list[str] = []
    total_size = 0
    file_count = 0
    truncated = False

    # Root directory header
    lines.append(f"{start_path.name}/")

    # Track parent paths and their "last child" status for tree drawing
    # Key: depth, Value: is_last_at_this_depth
    depth_last_map: dict[int, bool] = {}

    # Collect all entries first to know which is last at each level
    entries = list(
        tree_explore(
            start_path,
            max_depth=max_depth,
            max_files=effective_max_files,
            should_prune=combined_prune,
        )
    )

    # Check if truncated (use effective limit for comparison)
    if len(entries) >= effective_max_files:
        truncated = True

    # Group entries by parent to determine last child
    parent_children: dict[Path, list[FileEntry]] = {}
    for entry in entries:
        parent = entry.path.parent
        if parent not in parent_children:
            parent_children[parent] = []
        parent_children[parent].append(entry)

    # Build tree lines
    for entry in entries:
        depth = entry.depth
        parent = entry.path.parent

        # Determine if this is the last child of its parent
        siblings = parent_children.get(parent, [])
        is_last = entry == siblings[-1] if siblings else False
        depth_last_map[depth] = is_last

        # Build prefix based on ancestor "is_last" status
        prefix_parts = []
        for d in range(depth):
            if d in depth_last_map and depth_last_map[d]:
                prefix_parts.append(TREE_EMPTY)  # Parent was last, no vertical line
            else:
                prefix_parts.append(TREE_VERTICAL)  # Parent has more siblings

        # Current level connector
        connector = TREE_LAST if is_last else TREE_BRANCH

        prefix = "".join(prefix_parts) + connector

        # Format entry name
        if entry.is_dir:
            name = f"{entry.name}/"
        else:
            name = entry.name
            file_count += 1
            total_size += entry.size

        # Add size if requested
        if show_size and not entry.is_dir:
            size_str = format_size(entry.size)
            line = f"{prefix}{name} ({size_str})"
        else:
            line = f"{prefix}{name}"

        lines.append(line)

    # Add summary
    lines.append("")
    lines.append(f"📊 Stats: {file_count} files, {format_size(total_size)} total")
    if max_depth is not None:
        lines.append(f"   Max depth: {max_depth}")
    if truncated:
        lines.append(f"   ⚠️ Truncated at {effective_max_files} entries")

    return "\n".join(lines)


# Default prune function for common large directories
DEFAULT_PRUNE_DIRS = frozenset(
    {
        "node_modules",
        ".git",
        ".svn",
        ".hg",
        "__pycache__",
        ".venv",
        "venv",
        ".env",
        "env",
        ".tox",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "dist",
        "build",
        ".next",
        ".nuxt",
        "target",  # Rust/Maven
        "vendor",  # Go/PHP
    }
)


def default_should_prune(path: Path) -> bool:
    """Default pruning function to skip common large directories.

    Skips: node_modules, .git, __pycache__, .venv, etc.
    """
    return path.name in DEFAULT_PRUNE_DIRS
