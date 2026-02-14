"""DeepScan Progress Module.

Progress streaming, escalation management, and session validation utilities.
"""

from __future__ import annotations

__all__ = [
    # Utility functions
    "should_escalate",
    "classify_failure",
    "validate_session_hash",
    # Classes
    "EscalationBudget",
    "ProgressWriter",
]

import json
from datetime import datetime
from pathlib import Path

from constants import DEFAULT_PROGRESS_MAX_SIZE
from models import SESSION_HASH_PATTERN, FailureType


def should_escalate(failure_type: FailureType, attempt: int) -> bool:
    """Determine if failure warrants model escalation.

    Phase 4: Only escalate for quality/complexity failures after retry.

    Args:
        failure_type: Type of failure that occurred.
        attempt: Current attempt number (1-indexed).

    Returns:
        True if should escalate to more capable model.
    """
    # Never escalate these failure types
    if failure_type in (
        FailureType.TIMEOUT,
        FailureType.PARSE_ERROR,
        FailureType.RATE_LIMIT,
        FailureType.UNKNOWN,
    ):
        return False

    # Escalate quality/complexity failures after 1 retry (attempt >= 2)
    if failure_type in (FailureType.QUALITY_LOW, FailureType.COMPLEXITY):
        return attempt >= 2

    return False


def classify_failure(error_message: str | None, response_length: int = 0) -> FailureType:
    """Classify failure type from error message and response characteristics.

    Args:
        error_message: Error message from sub-agent (can be None).
        response_length: Length of response (for quality detection).

    Returns:
        Classified failure type.
    """
    error_lower = error_message.lower() if error_message else ""

    # Check error message patterns first
    if "timeout" in error_lower or "timed out" in error_lower:
        return FailureType.TIMEOUT
    if "rate limit" in error_lower or "rate_limit" in error_lower:
        return FailureType.RATE_LIMIT
    if "json" in error_lower or "parse" in error_lower or "format" in error_lower:
        return FailureType.PARSE_ERROR
    if "complex" in error_lower or "too large" in error_lower:
        return FailureType.COMPLEXITY

    # Issue 5: Distinguish between no response (0) and short response (1-49)
    # response_length=0 with no error message is UNKNOWN (could be connection issue)
    # response_length=0 with error message was already classified above
    # response_length 1-49 is QUALITY_LOW (model responded but poorly)
    if response_length == 0:
        # No response at all - likely a connection or other issue
        return FailureType.UNKNOWN
    if response_length < 50:
        # Very short response - quality issue
        return FailureType.QUALITY_LOW

    return FailureType.UNKNOWN


class EscalationBudget:
    """Track and limit model escalation to control costs.

    Phase 4: Prevents runaway costs from excessive escalation.
    """

    def __init__(
        self,
        max_escalation_ratio: float = 0.15,
        max_sonnet_cost_usd: float = 5.0,
    ):
        self.max_escalation_ratio = max_escalation_ratio
        self.max_sonnet_cost_usd = max_sonnet_cost_usd
        self.escalation_count = 0
        self.total_chunks = 0
        self.estimated_sonnet_cost = 0.0

    def can_escalate(self) -> bool:
        """Check if escalation is allowed within budget."""
        if self.total_chunks == 0:
            return True

        ratio_ok = (self.escalation_count / self.total_chunks) < self.max_escalation_ratio
        cost_ok = self.estimated_sonnet_cost < self.max_sonnet_cost_usd

        return ratio_ok and cost_ok

    def record_escalation(self, estimated_cost: float = 0.01):
        """Record an escalation event."""
        self.escalation_count += 1
        self.estimated_sonnet_cost += estimated_cost

    def set_total_chunks(self, total: int):
        """Set total chunk count for ratio calculation."""
        self.total_chunks = total


class ProgressWriter:
    """Write progress events to JSONL file for real-time monitoring.

    Phase 4: Enables `tail -f` style progress monitoring for CLI users.

    Events are written as newline-delimited JSON (JSONL) format.
    File size is limited to prevent disk space issues during large operations.
    When the file exceeds max_size, it's rotated (old file renamed to .1).
    """

    def __init__(self, session_dir: Path, max_size: int = DEFAULT_PROGRESS_MAX_SIZE):
        """Initialize progress writer.

        Args:
            session_dir: Directory for session files.
            max_size: Maximum file size in bytes before rotation (default: 10MB).
        """
        self.progress_file = session_dir / "progress.jsonl"
        self.max_size = max_size
        self._file = None
        self._current_size = 0

    def __enter__(self):
        # Check existing file size
        if self.progress_file.exists():
            self._current_size = self.progress_file.stat().st_size
        self._file = self.progress_file.open("a", encoding="utf-8")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._file:
            self._file.close()
            self._file = None

    def _rotate_if_needed(self) -> None:
        """Rotate file if it exceeds max size."""
        if self._current_size >= self.max_size:
            # Close current file
            if self._file:
                self._file.close()

            # Rotate: rename current to .1 (overwrites any existing .1)
            rotated_file = self.progress_file.with_suffix(".jsonl.1")
            if rotated_file.exists():
                rotated_file.unlink()
            self.progress_file.rename(rotated_file)

            # Reopen fresh file
            self._file = self.progress_file.open("a", encoding="utf-8")
            self._current_size = 0

    def emit(self, event_type: str, **data) -> None:
        """Emit a progress event.

        Args:
            event_type: Type of event (batch_start, chunk_complete, finding, batch_end).
            **data: Additional event data.
        """
        if not self._file:
            return

        event = {
            "type": event_type,
            "ts": datetime.now().isoformat(),
            **data,
        }
        line = json.dumps(event) + "\n"
        self._file.write(line)
        self._file.flush()  # Immediate visibility for tail -f

        # Track size and rotate if needed
        self._current_size += len(line.encode("utf-8"))
        self._rotate_if_needed()

    def emit_batch_start(self, batch_num: int, total_batches: int, chunk_count: int) -> None:
        """Emit batch start event."""
        self.emit("batch_start", batch=batch_num, total=total_batches, chunks=chunk_count)

    def emit_batch_end(self, batch_num: int, success: int, failed: int) -> None:
        """Emit batch end event."""
        self.emit("batch_end", batch=batch_num, success=success, failed=failed)

    def emit_chunk_complete(self, chunk_id: str, findings_count: int, status: str) -> None:
        """Emit chunk completion event."""
        self.emit("chunk_complete", chunk_id=chunk_id, findings=findings_count, status=status)

    def emit_finding(self, chunk_id: str, point: str, confidence: str) -> None:
        """Emit individual finding event."""
        self.emit("finding", chunk_id=chunk_id, point=point[:100], confidence=confidence)

    def emit_escalation(self, chunk_id: str, from_model: str, to_model: str) -> None:
        """Emit model escalation event."""
        self.emit("escalation", chunk_id=chunk_id, from_model=from_model, to_model=to_model)


def validate_session_hash(session_hash: str) -> bool:
    """Validate session hash to prevent path traversal.

    Args:
        session_hash: Session identifier to validate.

    Returns:
        True if valid, False otherwise.
    """
    if not session_hash:
        return False
    if not SESSION_HASH_PATTERN.match(session_hash):
        return False
    if ".." in session_hash or "/" in session_hash or "\\" in session_hash:
        return False
    return True
