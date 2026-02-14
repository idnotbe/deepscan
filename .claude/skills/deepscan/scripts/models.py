"""Pydantic data models for DeepScan state management.

All state is serialized to JSON (no pickle) for security and portability.
"""

from __future__ import annotations

__all__ = [
    # Constants
    "SESSION_HASH_PATTERN",
    "MAX_CHECKPOINT_WRITE_SIZE",
    "MAX_CHECKPOINT_READ_SIZE",
    "MAX_CHECKPOINT_SIZE",
    # Exceptions
    "LazyModeError",
    # Enums
    "FailureType",
    "ScanMode",
    # Data Models
    "ChunkInfo",
    "Finding",
    "ChunkResult",
    "ContextMetadata",
    "DeepScanConfig",
    "DeepScanState",
]

import re
import secrets
import time
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# =============================================================================
# Security Constants (shared across modules)
# =============================================================================

# Valid session hash pattern (alphanumeric, underscore, hyphen only)
# Used by CheckpointManager and StateManager for path traversal prevention
SESSION_HASH_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")

# Checkpoint size limits (asymmetric for backward compatibility)
# See DEEPSCAN_REVIEW_2026-01-21.md §2.1 for rationale.
#
# WRITE limit: Enforced on new checkpoints to prevent future bloat.
# Typical checkpoint is ~500KB (1000 chunks). 20MB allows ~4,000-10,000 chunks
# with realistic findings (not 40K - that's only with empty results).
MAX_CHECKPOINT_WRITE_SIZE = 20 * 1024 * 1024

# READ limit: Higher to preserve backward compatibility with legacy checkpoints.
# Existing checkpoints up to 100MB will load (with warning if >20MB).
# This prevents silent data loss for users who have large checkpoints.
MAX_CHECKPOINT_READ_SIZE = 100 * 1024 * 1024

# Legacy alias (deprecated, use specific limits above)
MAX_CHECKPOINT_SIZE = MAX_CHECKPOINT_WRITE_SIZE


# =============================================================================
# Custom Exceptions
# =============================================================================


class LazyModeError(RuntimeError):
    """Raised when an operation requires full context which is not loaded in lazy mode.

    This exception is raised to clearly signal to AI agents that the operation
    cannot be performed because the global context is not loaded. The error message
    includes recovery instructions to guide the agent's next action.

    Example:
        >>> grep("pattern")  # In lazy mode
        LazyModeError: grep() requires global context which is not loaded in lazy mode.
        Use grep_file(pattern, 'path/to/file') to search specific files.
    """

    pass


class FailureType(str, Enum):
    """Types of sub-agent failures for escalation decision.

    Phase 4: Only quality/complexity failures trigger model escalation.
    """

    TIMEOUT = "timeout"  # Don't escalate - larger models are slower
    PARSE_ERROR = "parse_error"  # Don't escalate - fix prompt instead
    RATE_LIMIT = "rate_limit"  # Don't escalate - retry same model
    QUALITY_LOW = "quality_low"  # ESCALATE - model capability issue
    COMPLEXITY = "complexity"  # ESCALATE - code too complex for model
    UNKNOWN = "unknown"  # Don't escalate by default


class ScanMode(str, Enum):
    """Scan mode for DeepScan traversal strategy.

    Phase 1 (Lazy Mode): Defines what to visit/load.
    - FULL: Load everything, chunk, analyze all (current eager behavior)
    - LAZY: Depth-limited traversal, metadata only initially
    - TARGETED: Specific files/patterns only
    """

    FULL = "full"  # Current eager behavior (default)
    LAZY = "lazy"  # Structure only, lazy loading
    TARGETED = "targeted"  # Specific files/patterns


class ChunkInfo(BaseModel):
    """Metadata for a single chunk of context."""

    chunk_id: str
    file_path: str
    start_offset: int
    end_offset: int
    size: int
    status: str = "pending"  # pending, processing, completed, failed
    processed_at: datetime | None = None


class Finding(BaseModel):
    """A single finding from sub-agent analysis."""

    point: str
    evidence: str
    confidence: str = "medium"  # high, medium, low
    location: dict[str, Any] | None = None
    verification_required: bool = False  # P3.3-FIX: Track if finding needs verification


class ChunkResult(BaseModel):
    """Result from processing a single chunk."""

    chunk_id: str
    status: str  # completed, partial, failed
    findings: list[Finding] = Field(default_factory=list)
    missing_info: list[str] = Field(default_factory=list)
    suggested_queries: list[str] = Field(default_factory=list)  # FIX: Missing field from spec
    partial_answer: str | None = None
    error: str | None = None
    processed_at: datetime = Field(default_factory=datetime.now)


class ContextMetadata(BaseModel):
    """Metadata about the loaded context."""

    path: str
    loaded_at: datetime
    total_size: int
    encoding: str = "utf-8"
    is_directory: bool = False
    file_count: int = 1


class DeepScanConfig(BaseModel):
    """Configuration for DeepScan processing."""

    chunk_size: int = 150000
    chunk_overlap: int = 0  # FIX: Architecture spec default is 0, not 10000
    max_parallel_agents: int = 5  # FIX: Missing field from architecture spec
    max_retries: int = 3
    timeout_seconds: int = 300

    # Phase 4: Adaptive chunking
    adaptive_chunking: bool = False  # Opt-in feature
    detected_content_type: str | None = None  # Set at init (e.g., "code:.py", "docs:.md")

    # Phase 4: Model escalation
    enable_escalation: bool = True  # Auto-upgrade on failures
    max_escalation_ratio: float = 0.15  # Max 15% of chunks can escalate
    max_sonnet_cost_usd: float = 5.0  # Cost cap for sonnet usage

    # Phase 5: Incremental re-analysis
    incremental_enabled: bool = False  # Opt-in feature
    previous_session: str | None = None  # Session hash for delta comparison
    changed_file_count: int = 0  # Number of changed/added files
    deleted_file_count: int = 0  # Number of deleted files

    # Phase 1 (Lazy Mode): Traversal strategy configuration
    scan_mode: ScanMode = ScanMode.FULL  # Default: eager full scan
    lazy_depth: int = 3  # Max directory depth for lazy traversal
    lazy_file_limit: int = 50  # Max files to show in lazy mode
    target_paths: list[str] = Field(default_factory=list)  # Paths for targeted mode

    # P8-FIX: Agent type specialization (Issue 1 from deepscan_errors_20260124.md)
    # Backend in subagent_prompt.py supports: general, security, architecture, performance
    agent_type: str = "general"  # Default to general-purpose analysis


class DeepScanState(BaseModel):
    """Main state object for DeepScan session.

    Serialized to JSON for persistence.
    """

    version: str = "2.0.0"
    session_id: str = Field(
        default_factory=lambda: f"deepscan_{int(time.time())}_{secrets.token_hex(8)}"
    )
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Configuration
    config: DeepScanConfig = Field(default_factory=DeepScanConfig)

    # Context
    context_meta: ContextMetadata | None = None
    query: str | None = None

    # Chunks
    chunks: list[ChunkInfo] = Field(default_factory=list)

    # Results
    results: list[ChunkResult] = Field(default_factory=list)
    buffers: list[str] = Field(default_factory=list)

    # Progress
    phase: str = "initialized"  # initialized, scouting, chunking, mapping, reducing, completed
    progress_percent: float = 0.0

    # Final output
    final_answer: str | None = None

    def model_post_init(self, __context: Any) -> None:
        """Update timestamp after model creation."""
        self.updated_at = datetime.now()
