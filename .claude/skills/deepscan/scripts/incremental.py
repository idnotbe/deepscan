"""Incremental re-analysis module for DeepScan Phase 5 & 7.

Provides file hash tracking and delta detection to enable incremental
re-analysis of codebases. Only changed files are re-processed, saving
time and compute costs.

Key Components:
- FileHash: Individual file hash record
- FileHashManifest: Collection of file hashes for a directory
- ChunkFileMapping: Tracks which chunks contain which files
- IncrementalAnalyzer: Main interface for incremental analysis

Phase 7 (P7-004):
- HashAlgorithm enum for algorithm selection
- xxHash support for 10-20x faster hashing
- Automatic fallback to SHA-256 if xxhash not installed

Security:
- Session hash validation prevents path traversal
- Symlinks are skipped to prevent infinite loops
- Paths are canonicalized for consistency
"""

from __future__ import annotations

__all__ = [
    # Functions
    "is_xxhash_available",
    "compute_file_hash",
    # Enums
    "HashAlgorithm",
    # Constants
    "DEFAULT_HASH_ALGORITHM",
    "DEFAULT_IGNORE_PATTERNS",
    # Data Models
    "ChunkMappingInfo",
    "FileHash",
    "FileDelta",
    "FileHashManifest",
    "ChunkFileMapping",
    # Main class
    "IncrementalAnalyzer",
]

import fnmatch
import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import TypedDict

from pydantic import BaseModel, Field, ValidationError

# Import SESSION_HASH_PATTERN from models (Single Source of Truth)
from models import SESSION_HASH_PATTERN

# P7-004: Optional xxhash import
try:
    import xxhash

    _XXHASH_AVAILABLE = True
except ImportError:
    _XXHASH_AVAILABLE = False


def is_xxhash_available() -> bool:
    """Check if xxhash library is installed.

    Returns:
        True if xxhash is available, False otherwise.
    """
    return _XXHASH_AVAILABLE


class HashAlgorithm(Enum):
    """Supported hash algorithms for file hashing.

    P7-004: xxHash provides 10-20x faster hashing than SHA-256.
    Use xxHash for large codebases where speed matters.
    SHA-256 provides cryptographic strength if needed.
    """

    SHA256 = "sha256"  # Cryptographic, slower
    XXHASH64 = "xxhash64"  # Fast, 64-bit hash
    XXHASH3 = "xxhash3"  # Fastest, 64-bit hash (xxHash3)


# Default algorithm: xxHash3 if available, otherwise SHA-256
DEFAULT_HASH_ALGORITHM = HashAlgorithm.XXHASH3 if _XXHASH_AVAILABLE else HashAlgorithm.SHA256

# Logger for this module
logger = logging.getLogger(__name__)

# SESSION_HASH_PATTERN is now imported from models.py (removed duplicate definition)


# ============================================================
# Constants
# ============================================================

DEFAULT_IGNORE_PATTERNS = [
    "__pycache__",
    "*.pyc",
    "*.pyo",
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    ".env",
    ".env.*",  # All .env variants (.env.local, .env.production, etc.)
    "*.log",
    ".DS_Store",
    "Thumbs.db",
    "*.key",  # Private keys
    "*.pem",  # Certificates/keys
    "credentials*",  # Credential files
    "*.secret",  # Secret files
]


# ============================================================
# TypedDict for ChunkFileMapping
# ============================================================


class ChunkMappingInfo(TypedDict):
    """Type definition for chunk mapping info."""

    chunk_id: str
    start_offset: int
    end_offset: int


# ============================================================
# File Hash Computation
# ============================================================


def compute_file_hash(
    file_path: Path,
    algorithm: HashAlgorithm = DEFAULT_HASH_ALGORITHM,
) -> str:
    """Compute hash of a file's content.

    Args:
        file_path: Path to the file to hash.
        algorithm: Hash algorithm to use (P7-004).
            - SHA256: 64-char hex, cryptographic
            - XXHASH64: 16-char hex, fast
            - XXHASH3: 16-char hex, fastest

    Returns:
        Hex string representing the file hash.
        Length varies by algorithm (64 for SHA256, 16 for xxHash).

    Raises:
        FileNotFoundError: If file doesn't exist.
        PermissionError: If file can't be read.

    Note:
        Falls back to SHA-256 if xxhash not installed and xxHash requested.
    """
    # Fall back to SHA-256 if xxhash not available
    if algorithm in (HashAlgorithm.XXHASH64, HashAlgorithm.XXHASH3) and not _XXHASH_AVAILABLE:
        logger.debug("xxhash not available, falling back to SHA-256")
        algorithm = HashAlgorithm.SHA256

    if algorithm == HashAlgorithm.SHA256:
        hasher = hashlib.sha256()
    elif algorithm == HashAlgorithm.XXHASH64:
        hasher = xxhash.xxh64()
    elif algorithm == HashAlgorithm.XXHASH3:
        hasher = xxhash.xxh3_64()
    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")

    with open(file_path, "rb") as f:
        # Read in 64KB chunks for memory efficiency
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


# ============================================================
# Data Models
# ============================================================


class FileHash(BaseModel):
    """Individual file hash record."""

    file_path: str
    sha256: str
    size: int = 0
    mtime: float = 0.0

    @classmethod
    def from_file(cls, file_path: Path, base_path: Path | None = None) -> FileHash:
        """Create FileHash from an actual file.

        Args:
            file_path: Absolute or relative path to the file.
            base_path: If provided, store relative path from this base.

        Returns:
            FileHash instance with computed hash.
        """
        abs_path = file_path.resolve()
        stat = abs_path.stat()

        # Store relative path if base_path provided
        if base_path:
            rel_path = str(abs_path.relative_to(base_path.resolve()))
        else:
            rel_path = str(abs_path)

        return cls(
            file_path=rel_path,
            sha256=compute_file_hash(abs_path),
            size=stat.st_size,
            mtime=stat.st_mtime,
        )


@dataclass
class FileDelta:
    """Result of comparing two FileHashManifests."""

    changed_files: list[str] = field(default_factory=list)
    added_files: list[str] = field(default_factory=list)
    deleted_files: list[str] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        """Check if any changes were detected."""
        return bool(self.changed_files or self.added_files or self.deleted_files)

    @property
    def total_changes(self) -> int:
        """Total number of changed, added, and deleted files."""
        return len(self.changed_files) + len(self.added_files) + len(self.deleted_files)


class FileHashManifest(BaseModel):
    """Collection of file hashes for a directory.

    Used to track file states and detect changes between analysis sessions.
    """

    file_hashes: dict[str, str] = Field(default_factory=dict)
    """Mapping of relative file path to hash (algorithm tracked separately)."""

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    """When this manifest was created (UTC)."""

    source_path: str = ""
    """Root directory this manifest was created from."""

    algorithm: str = Field(default_factory=lambda: DEFAULT_HASH_ALGORITHM.value)
    """Hash algorithm used (P7-004). One of: sha256, xxhash64, xxhash3."""

    @classmethod
    def from_directory(
        cls,
        directory: Path,
        ignore_patterns: list[str] | None = None,
        algorithm: HashAlgorithm | None = None,
    ) -> FileHashManifest:
        """Create manifest by scanning a directory.

        Args:
            directory: Root directory to scan.
            ignore_patterns: Glob patterns for files/dirs to ignore.
                Defaults to common patterns like __pycache__, .git, etc.
            algorithm: Hash algorithm to use (P7-004).
                Defaults to xxHash3 if available, otherwise SHA-256.

        Returns:
            FileHashManifest with hashes for all non-ignored files.
        """
        if ignore_patterns is None:
            ignore_patterns = DEFAULT_IGNORE_PATTERNS

        if algorithm is None:
            algorithm = DEFAULT_HASH_ALGORITHM

        file_hashes: dict[str, str] = {}
        base_path = directory.resolve()

        for file_path in base_path.rglob("*"):
            # Skip symlinks to prevent infinite loops and security issues
            if file_path.is_symlink():
                logger.debug(f"Skipping symlink: {file_path}")
                continue

            if not file_path.is_file():
                continue

            # Check ignore patterns
            rel_path = str(file_path.relative_to(base_path))
            if _should_ignore(rel_path, ignore_patterns):
                continue

            try:
                file_hash = compute_file_hash(file_path, algorithm=algorithm)
                file_hashes[rel_path] = file_hash
            except (PermissionError, OSError) as e:
                # Skip files we can't read
                logger.debug(f"Skipping unreadable file {file_path}: {e}")
                continue

        return cls(
            file_hashes=file_hashes,
            source_path=str(base_path),
            algorithm=algorithm.value,
        )

    def compare_with(self, previous: FileHashManifest) -> FileDelta:
        """Compare this manifest with a previous one to find changes.

        Args:
            previous: Earlier manifest to compare against.

        Returns:
            FileDelta with changed, added, and deleted files.
        """
        current_files = set(self.file_hashes.keys())
        previous_files = set(previous.file_hashes.keys())

        added = current_files - previous_files
        deleted = previous_files - current_files
        common = current_files & previous_files

        changed = sorted([f for f in common if self.file_hashes[f] != previous.file_hashes[f]])

        return FileDelta(
            changed_files=changed,
            added_files=sorted(added),
            deleted_files=sorted(deleted),
        )

    def save(self, path: Path) -> None:
        """Save manifest to JSON file.

        Args:
            path: File path to save to.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> FileHashManifest:
        """Load manifest from JSON file.

        Args:
            path: File path to load from.

        Returns:
            FileHashManifest instance.

        Raises:
            FileNotFoundError: If file doesn't exist.
            json.JSONDecodeError: If file is not valid JSON.
        """
        return cls.model_validate_json(path.read_text(encoding="utf-8"))


class ChunkFileMapping(BaseModel):
    """Tracks which chunks contain which files.

    Used to determine which chunks need re-processing when files change.
    """

    mappings: dict[str, list[ChunkMappingInfo]] = Field(default_factory=dict)
    """Mapping of file_path to list of chunk info."""

    def add(
        self,
        chunk_id: str,
        file_path: str,
        start_offset: int,
        end_offset: int,
    ) -> None:
        """Add a mapping from file to chunk.

        Args:
            chunk_id: ID of the chunk containing this file content.
            file_path: Path of the file.
            start_offset: Start byte offset within chunk.
            end_offset: End byte offset within chunk.
        """
        if file_path not in self.mappings:
            self.mappings[file_path] = []

        mapping_info: ChunkMappingInfo = {
            "chunk_id": chunk_id,
            "start_offset": start_offset,
            "end_offset": end_offset,
        }
        self.mappings[file_path].append(mapping_info)

    def get_chunks_for_file(self, file_path: str) -> list[str]:
        """Get all chunk IDs that contain a given file.

        Args:
            file_path: Path of the file to look up.

        Returns:
            List of chunk IDs containing this file's content.
        """
        if file_path not in self.mappings:
            return []
        return [m["chunk_id"] for m in self.mappings[file_path]]

    def get_affected_chunks(self, changed_files: list[str]) -> set[str]:
        """Get all chunks affected by a list of changed files.

        Args:
            changed_files: List of file paths that have changed.

        Returns:
            Set of chunk IDs that need re-processing.
        """
        affected: set[str] = set()
        for file_path in changed_files:
            affected.update(self.get_chunks_for_file(file_path))
        return affected


# ============================================================
# Incremental Analyzer
# ============================================================


class IncrementalAnalyzer:
    """Main interface for incremental re-analysis.

    Coordinates file hash tracking and delta detection across sessions.
    """

    def __init__(self, session_hash: str, cache_root: Path | None = None):
        """Initialize analyzer for a session.

        Args:
            session_hash: Hash identifying the DeepScan session.
            cache_root: Root cache directory. Defaults to ~/.claude/cache/deepscan

        Raises:
            ValueError: If session_hash contains invalid characters.
        """
        # Validate session_hash to prevent path traversal attacks
        if not SESSION_HASH_PATTERN.match(session_hash):
            raise ValueError(
                f"Invalid session_hash: '{session_hash}'. "
                "Must contain only alphanumeric characters, underscores, and hyphens."
            )

        self.session_hash = session_hash

        if cache_root is None:
            cache_root = Path.home() / ".claude" / "cache" / "deepscan"

        self.cache_root = cache_root
        self.session_dir = cache_root / session_hash
        self.manifest_path = self.session_dir / "file_hashes.json"

    def get_previous_manifest(self) -> FileHashManifest | None:
        """Load the previous session's file hash manifest.

        Returns:
            FileHashManifest if exists, None otherwise.

        Note:
            Returns None for missing, corrupted, or invalid manifest files.
            This is intentional - we treat these cases as "no previous state".
        """
        # Directly try to load - avoids race condition from exists() check
        try:
            return FileHashManifest.load(self.manifest_path)
        except FileNotFoundError:
            return None
        except (ValidationError, ValueError) as e:
            logger.warning(f"Corrupted or invalid manifest at {self.manifest_path}: {e}")
            return None

    def save_manifest(self, manifest: FileHashManifest) -> None:
        """Save file hash manifest for this session.

        Args:
            manifest: Manifest to save.
        """
        manifest.save(self.manifest_path)

    def get_affected_chunks(
        self,
        source_directory: Path,
        ignore_patterns: list[str] | None = None,
    ) -> FileDelta:
        """Determine which files have changed since last analysis.

        Args:
            source_directory: Directory to analyze.
            ignore_patterns: Patterns to ignore.

        Returns:
            FileDelta with changed, added, and deleted files.
        """
        # Create current manifest
        current = FileHashManifest.from_directory(source_directory, ignore_patterns)

        # Load previous manifest
        previous = self.get_previous_manifest()

        if previous is None:
            # No previous manifest = all files are "added"
            return FileDelta(
                added_files=list(current.file_hashes.keys()),
            )

        return current.compare_with(previous)


# ============================================================
# Helper Functions
# ============================================================


def _should_ignore(path: str, patterns: list[str]) -> bool:
    """Check if a path should be ignored based on patterns.

    Args:
        path: Relative path to check.
        patterns: List of glob patterns.

    Returns:
        True if path matches any ignore pattern.
    """
    # Check each component of the path
    parts = Path(path).parts
    for pattern in patterns:
        # Check full path
        if fnmatch.fnmatch(path, pattern):
            return True
        # Check path components (for directory patterns like __pycache__)
        for part in parts:
            if fnmatch.fnmatch(part, pattern):
                return True
    return False
