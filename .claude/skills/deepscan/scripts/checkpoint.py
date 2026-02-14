"""Checkpoint management for DeepScan session recovery.

Implements ARCH_05 §1: CheckpointManager for saving/loading session state.
Enables resume capability after interruption or crash.

Phase 6 Updates:
- Issue N Fix: Windows atomic write retry loop for file locking
- Cancellation support: Check cancellation flag during retry
"""

from __future__ import annotations

__all__ = [
    # Exceptions
    "CheckpointTooLargeError",
    # Data Models
    "Checkpoint",
    # Manager
    "CheckpointManager",
    # Utility functions
    "restore_state_from_checkpoint",
]

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

# Import shared security constants from models
from models import (
    MAX_CHECKPOINT_READ_SIZE,
    MAX_CHECKPOINT_WRITE_SIZE,
    SESSION_HASH_PATTERN,
)
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from cancellation import CancellationManager
    from models import DeepScanState

logger = logging.getLogger(__name__)


class CheckpointTooLargeError(Exception):
    """Raised when checkpoint file exceeds maximum read size.

    This is a critical error indicating potential data corruption or
    an unexpectedly large checkpoint that cannot be safely loaded.
    """

    pass


class Checkpoint(BaseModel):
    """Checkpoint data for session recovery.

    Stores the minimal state needed to resume processing.
    """

    checkpoint_id: str
    session_id: str
    phase: str
    batch_index: int
    completed_chunks: list[str]
    pending_chunks: list[str]
    partial_results: list[dict] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)


class CheckpointManager:
    """Manages checkpoints for session recovery.

    Saves checkpoint after each batch completion.
    Enables resume from last successful checkpoint.

    Usage:
        checkpoint_mgr = CheckpointManager(session_hash)
        checkpoint_mgr.save_checkpoint(state, batch_index)
        existing = checkpoint_mgr.load_checkpoint()
        checkpoint_mgr.clear_checkpoint()
    """

    def __init__(self, session_hash: str, cache_root: Path | None = None):
        """Initialize checkpoint manager.

        Args:
            session_hash: Unique session identifier.
            cache_root: Root directory for cache (default: ~/.claude/cache/deepscan).

        Raises:
            ValueError: If session_hash contains invalid characters or path traversal.
        """
        # SECURITY: Validate session_hash to prevent path traversal
        if not SESSION_HASH_PATTERN.match(session_hash):
            raise ValueError(
                f"Invalid session_hash: must be alphanumeric with hyphens/underscores only, "
                f"got: {session_hash!r}"
            )
        if ".." in session_hash:
            raise ValueError("Invalid session_hash: path traversal not allowed")

        self.cache_root = cache_root or (Path.home() / ".claude" / "cache" / "deepscan")
        self.cache_dir = self.cache_root / session_hash

        # SECURITY: Additional path traversal check after resolution
        try:
            resolved = self.cache_dir.resolve()
            resolved.relative_to(self.cache_root.resolve())
        except ValueError as err:
            raise ValueError(
                f"Path traversal detected: {session_hash} resolves outside cache root"
            ) from err

        self.checkpoint_file = self.cache_dir / "checkpoint.json"

    def save_checkpoint(
        self,
        state: DeepScanState,
        batch_index: int,
        cancel_mgr: CancellationManager | None = None,
        max_retries: int = 3,
        retry_delay: float = 0.1,
    ) -> Checkpoint:
        """Save checkpoint after batch completion.

        Atomic write: writes to temp file, then renames.
        Includes Windows retry loop for file locking issues (Issue N Fix).

        Args:
            state: Current DeepScan state.
            batch_index: Index of completed batch.
            cancel_mgr: Optional CancellationManager for cancellation checks.
            max_retries: Maximum retry attempts for Windows file locking.
            retry_delay: Delay between retries in seconds.

        Returns:
            Created Checkpoint object.

        Raises:
            PermissionError: If write fails after all retries.
        """
        # Collect completed and pending chunk IDs
        completed_chunks = [c.chunk_id for c in state.chunks if c.status == "completed"]
        pending_chunks = [c.chunk_id for c in state.chunks if c.status == "pending"]

        # Convert results to dict for serialization
        partial_results = [r.model_dump() for r in state.results]

        checkpoint = Checkpoint(
            checkpoint_id=f"cp_{int(time.time())}",
            session_id=state.session_id,
            phase=state.phase,
            batch_index=batch_index,
            completed_chunks=completed_chunks,
            pending_chunks=pending_chunks,
            partial_results=partial_results,
            created_at=datetime.now(),
        )

        # Atomic write with Windows retry (Issue N Fix)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        tmp_file = self.checkpoint_file.with_suffix(".json.tmp")
        checkpoint_json = checkpoint.model_dump_json(indent=2)
        tmp_file.write_text(checkpoint_json, encoding="utf-8")

        # Telemetry: Log checkpoint size for monitoring
        checkpoint_size = len(checkpoint_json.encode("utf-8"))
        logger.debug(
            f"Saving checkpoint: {checkpoint_size} bytes "
            f"({checkpoint_size / 1024:.1f} KB, {len(completed_chunks)} completed, "
            f"{len(pending_chunks)} pending)"
        )

        # Warn if checkpoint exceeds recommended write size (asymmetric limit)
        if checkpoint_size > MAX_CHECKPOINT_WRITE_SIZE:
            logger.warning(
                f"Checkpoint size ({checkpoint_size} bytes) exceeds recommended limit "
                f"({MAX_CHECKPOINT_WRITE_SIZE} bytes). Future loads may require legacy mode. "
                f"Consider reducing partial_results or completed_chunks."
            )

        # Retry loop for Windows file locking issues
        for attempt in range(max_retries):
            # IMPORTANT: Only abort on Force Quit, not Graceful Cancellation!
            # Graceful cancellation's purpose is to SAVE progress before exiting.
            # Force quit (double tap) means user wants to exit immediately.
            if cancel_mgr and cancel_mgr.is_force_quit():
                # Clean up temp file on force quit
                try:
                    tmp_file.unlink(missing_ok=True)
                except Exception:
                    pass
                logger.warning("Checkpoint save interrupted by Force Quit")
                # Still return checkpoint even if not saved to file
                return checkpoint

            try:
                # os.replace is atomic on POSIX and mostly atomic on Windows
                os.replace(str(tmp_file), str(self.checkpoint_file))
                logger.debug(f"Checkpoint saved: {checkpoint.checkpoint_id}")
                return checkpoint

            except PermissionError as e:
                if attempt < max_retries - 1:
                    logger.debug(
                        f"File locked during checkpoint save, retrying in {retry_delay}s: {e}"
                    )
                    time.sleep(retry_delay)
                else:
                    # Clean up temp file before raising
                    try:
                        tmp_file.unlink(missing_ok=True)
                    except Exception:
                        pass

                    logger.error(f"Failed to save checkpoint after {max_retries} attempts: {e}")
                    raise

        return checkpoint

    def load_checkpoint(self) -> Checkpoint | None:
        """Load existing checkpoint if available.

        Returns:
            Checkpoint object if exists, None otherwise.
        """
        try:
            if not self.checkpoint_file.exists():
                return None

            # SECURITY: Check file size before reading to prevent DoS
            # Uses asymmetric limits for backward compatibility:
            # - READ limit (100MB): Allows loading legacy checkpoints
            # - WRITE limit (20MB): Used for "over recommended" warning
            file_size = self.checkpoint_file.stat().st_size

            if file_size > MAX_CHECKPOINT_READ_SIZE:
                # Absolute limit - file too large even for legacy support
                logger.error(
                    f"Checkpoint file exceeds maximum read limit: {file_size} bytes "
                    f"(max {MAX_CHECKPOINT_READ_SIZE}). Cannot load - data may be corrupted."
                )
                raise CheckpointTooLargeError(
                    f"Checkpoint file too large: {file_size} bytes exceeds "
                    f"{MAX_CHECKPOINT_READ_SIZE} byte limit"
                )

            if file_size > MAX_CHECKPOINT_WRITE_SIZE:
                # Legacy checkpoint - load with warning
                logger.warning(
                    f"Loading legacy checkpoint: {file_size} bytes exceeds recommended "
                    f"limit of {MAX_CHECKPOINT_WRITE_SIZE} bytes. Consider pruning results."
                )

            # Telemetry: Log checkpoint size for monitoring
            logger.debug(
                f"Loading checkpoint: {file_size} bytes "
                f"({file_size / 1024:.1f} KB, {file_size / MAX_CHECKPOINT_WRITE_SIZE * 100:.1f}% of write limit)"
            )

            data = json.loads(self.checkpoint_file.read_text(encoding="utf-8"))
            return Checkpoint.model_validate(data)
        except FileNotFoundError:
            return None
        except (json.JSONDecodeError, ValueError, OSError) as e:
            logger.warning(f"Failed to load checkpoint: {type(e).__name__}: {e}")
            return None

    def clear_checkpoint(self) -> bool:
        """Clear checkpoint after successful completion.

        Returns:
            True if checkpoint was deleted, False if not found.
        """
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
            return True
        return False

    def has_checkpoint(self) -> bool:
        """Check if checkpoint exists.

        Returns:
            True if checkpoint file exists.
        """
        return self.checkpoint_file.exists()

    def get_checkpoint_info(self) -> dict | None:
        """Get checkpoint summary without full load.

        Returns:
            Summary dict or None if no checkpoint.
        """
        checkpoint = self.load_checkpoint()
        if not checkpoint:
            return None

        return {
            "checkpoint_id": checkpoint.checkpoint_id,
            "session_id": checkpoint.session_id,
            "phase": checkpoint.phase,
            "batch_index": checkpoint.batch_index,
            "completed_count": len(checkpoint.completed_chunks),
            "pending_count": len(checkpoint.pending_chunks),
            "created_at": checkpoint.created_at.isoformat(),
        }


def restore_state_from_checkpoint(
    state: DeepScanState,
    checkpoint: Checkpoint,
) -> None:
    """Restore DeepScan state from checkpoint.

    Modifies state in-place to match checkpoint.

    Args:
        state: DeepScanState to update.
        checkpoint: Checkpoint to restore from.
    """
    # Mark completed chunks
    for chunk_id in checkpoint.completed_chunks:
        for chunk in state.chunks:
            if chunk.chunk_id == chunk_id:
                chunk.status = "completed"

    # Restore phase and results
    state.phase = checkpoint.phase

    # Import here to avoid circular dependency
    from models import ChunkResult

    state.results = [ChunkResult.model_validate(r) for r in checkpoint.partial_results]

    # Update progress
    total = len(state.chunks)
    completed = len(checkpoint.completed_chunks)
    state.progress_percent = (completed / total * 100) if total > 0 else 0
