"""DeepScan Error Code System (Phase 6).

Structured error codes for better UX, automation, and support.

Error Code Format:
- Internal: DS_NNN_SLUG (Enum member name)
- Display: [DS-NNN] Title: message

Categories:
- DS-0XX: Input/Validation
- DS-1XX: Parsing/Processing
- DS-2XX: Chunking/Aggregation
- DS-3XX: Resource/File
- DS-4XX: Configuration
- DS-5XX: System/Internal
"""

from __future__ import annotations

__all__ = [
    # Enums
    "ErrorCategory",
    "ErrorCode",
    # Data Models
    "ErrorContext",
    "DeepScanError",
    # Utility functions
    "get_remediation",
    "get_exit_code",
    "handle_error",
]

import json
from enum import Enum

from pydantic import BaseModel, ConfigDict


class ErrorCategory(str, Enum):
    """Error code categories."""

    VALIDATION = "validation"
    PARSING = "parsing"
    CHUNKING = "chunking"
    RESOURCE = "resource"
    CONFIG = "config"
    SYSTEM = "system"


class ErrorCode(Enum):
    """DeepScan error codes.

    Format: DS_NNN_SLUG
    - NNN: 3-digit code
    - SLUG: Human-readable identifier

    Each member is a tuple: (code, title, category)
    """

    # DS-0XX: Input/Validation
    DS_001_INVALID_CONTEXT_PATH = (1, "Invalid Context Path", ErrorCategory.VALIDATION)
    DS_002_INVALID_SESSION_HASH = (2, "Invalid Session Hash", ErrorCategory.VALIDATION)
    DS_003_MISSING_QUERY = (3, "Missing Query", ErrorCategory.VALIDATION)
    DS_004_INVALID_CHUNK_SIZE = (4, "Invalid Chunk Size", ErrorCategory.VALIDATION)
    DS_005_OVERLAP_EXCEEDS_SIZE = (5, "Overlap Exceeds Size", ErrorCategory.VALIDATION)
    DS_006_EMPTY_CONTEXT = (6, "Empty Context", ErrorCategory.VALIDATION)

    # DS-1XX: Parsing/Processing
    DS_101_AST_PARSE_FAILED = (101, "AST Parse Failed", ErrorCategory.PARSING)
    DS_102_JSON_DECODE_ERROR = (102, "JSON Decode Error", ErrorCategory.PARSING)
    DS_103_ENCODING_ERROR = (103, "Encoding Error", ErrorCategory.PARSING)
    DS_104_SUBAGENT_PARSE_FAILED = (104, "Sub-agent Parse Failed", ErrorCategory.PARSING)
    DS_105_CHECKPOINT_CORRUPT = (105, "Checkpoint Corrupt", ErrorCategory.PARSING)

    # DS-2XX: Chunking/Aggregation
    DS_201_CHUNK_TOO_LARGE = (201, "Chunk Too Large", ErrorCategory.CHUNKING)
    DS_202_NO_CHUNKS_CREATED = (202, "No Chunks Created", ErrorCategory.CHUNKING)
    DS_203_AGGREGATION_CONFLICT = (203, "Aggregation Conflict", ErrorCategory.CHUNKING)
    DS_204_RESULT_VALIDATION_FAILED = (204, "Result Validation Failed", ErrorCategory.CHUNKING)
    DS_205_BATCH_FAILED = (205, "Batch Failed", ErrorCategory.CHUNKING)

    # DS-3XX: Resource/File
    DS_301_FILE_NOT_FOUND = (301, "File Not Found", ErrorCategory.RESOURCE)
    DS_302_PERMISSION_DENIED = (302, "Permission Denied", ErrorCategory.RESOURCE)
    DS_303_FILE_TOO_LARGE = (303, "File Too Large", ErrorCategory.RESOURCE)
    DS_304_CONTEXT_TOO_LARGE = (304, "Context Too Large", ErrorCategory.RESOURCE)
    DS_305_CACHE_DIR_ERROR = (305, "Cache Directory Error", ErrorCategory.RESOURCE)
    DS_306_SESSION_NOT_FOUND = (306, "Session Not Found", ErrorCategory.RESOURCE)

    # DS-4XX: Configuration
    DS_401_INVALID_CONFIG_FILE = (401, "Invalid Config File", ErrorCategory.CONFIG)
    DS_402_MISSING_REQUIRED_SETTING = (402, "Missing Required Setting", ErrorCategory.CONFIG)
    DS_403_INVALID_MODEL_SETTING = (403, "Invalid Model Setting", ErrorCategory.CONFIG)
    DS_404_ESCALATION_BUDGET_EXCEEDED = (404, "Escalation Budget Exceeded", ErrorCategory.CONFIG)

    # DS-5XX: System/Internal
    DS_501_INTERNAL_ERROR = (501, "Internal Error", ErrorCategory.SYSTEM)
    DS_502_STATE_CORRUPTION = (502, "State Corruption", ErrorCategory.SYSTEM)
    DS_503_TIMEOUT_ERROR = (503, "Timeout Error", ErrorCategory.SYSTEM)
    DS_504_RATE_LIMIT_ERROR = (504, "Rate Limit Error", ErrorCategory.SYSTEM)
    DS_505_CANCELLED_BY_USER = (505, "Cancelled By User", ErrorCategory.SYSTEM)

    def __init__(self, code: int, title: str, category: ErrorCategory):
        self._code = code
        self._title = title
        self._category = category

    @property
    def code(self) -> int:
        """Numeric error code."""
        return self._code

    @property
    def code_str(self) -> str:
        """Formatted code string (DS-NNN)."""
        return f"DS-{self._code:03d}"

    @property
    def title(self) -> str:
        """Human-readable title."""
        return self._title

    @property
    def category(self) -> ErrorCategory:
        """Error category."""
        return self._category

    @property
    def doc_url(self) -> str:
        """Documentation URL for this error code."""
        return f"https://deepscan.io/docs/errors/{self.code_str}"


class ErrorContext(BaseModel):
    """Context information for error reporting.

    All fields are optional since errors can occur at various points
    where some context may not be available.
    """

    model_config = ConfigDict(extra="ignore")  # Forward compatibility

    file_path: str | None = None
    chunk_id: str | None = None
    session_id: str | None = None
    expected: str | None = None
    actual: str | None = None
    extra: dict = {}


class DeepScanError(Exception):
    """Structured DeepScan exception.

    Provides:
    - Structured error code
    - Human-readable message
    - Context for debugging
    - JSON serialization for automation
    - Cause chain for root cause analysis

    Usage:
        raise DeepScanError(
            code=ErrorCode.DS_301_FILE_NOT_FOUND,
            message="Could not access source file",
            context=ErrorContext(file_path="/path/to/file.py")
        )
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        context: ErrorContext | None = None,
        cause: Exception | None = None,
    ):
        self.code = code
        self.message = message
        self.context = context or ErrorContext()
        self.cause = cause
        super().__init__(self.format_message())

    def format_message(self) -> str:
        """Format error for display."""
        parts = [f"[{self.code.code_str}] {self.code.title}: {self.message}"]

        if self.context.file_path:
            parts.append(f"  File: {self.context.file_path}")
        if self.context.chunk_id:
            parts.append(f"  Chunk: {self.context.chunk_id}")
        if self.context.expected and self.context.actual:
            parts.append(f"  Expected: {self.context.expected}")
            parts.append(f"  Actual: {self.context.actual}")

        return "\n".join(parts)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "error_code": self.code.code_str,
            "error_slug": self.code.name,
            "category": self.code.category.value,
            "title": self.code.title,
            "message": self.message,
            "context": self.context.model_dump(),
            "doc_url": self.code.doc_url,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


# =============================================================================
# Remediation Templates
# =============================================================================

# Template strings support {field} placeholders from ErrorContext
REMEDIATION_TEMPLATES: dict[ErrorCode, str] = {
    # Validation
    ErrorCode.DS_001_INVALID_CONTEXT_PATH: (
        "Check that the path exists and is accessible. Path: {file_path}"
    ),
    ErrorCode.DS_002_INVALID_SESSION_HASH: (
        "Session hash must contain only alphanumeric characters, underscores, and hyphens."
    ),
    ErrorCode.DS_003_MISSING_QUERY: (
        "Provide a query with -q/--query option or set it during init."
    ),
    ErrorCode.DS_004_INVALID_CHUNK_SIZE: (
        "Chunk size must be between 50,000 and 300,000 characters. "
        "Expected: {expected}, Got: {actual}"
    ),
    ErrorCode.DS_005_OVERLAP_EXCEEDS_SIZE: (
        "Overlap must be less than chunk size. Expected: <{expected}, Got: {actual}"
    ),
    ErrorCode.DS_006_EMPTY_CONTEXT: (
        "No files found in context path. Check the path contains analyzable files."
    ),
    # Parsing
    ErrorCode.DS_101_AST_PARSE_FAILED: (
        "Try disabling semantic chunking with --no-semantic flag. File: {file_path}"
    ),
    ErrorCode.DS_102_JSON_DECODE_ERROR: ("Verify the JSON file is valid. File: {file_path}"),
    ErrorCode.DS_103_ENCODING_ERROR: (
        "Ensure the file is UTF-8 encoded or specify encoding explicitly. File: {file_path}"
    ),
    ErrorCode.DS_104_SUBAGENT_PARSE_FAILED: (
        "Sub-agent response was malformed. Check the chunk content for issues."
    ),
    ErrorCode.DS_105_CHECKPOINT_CORRUPT: (
        "Checkpoint file is corrupted. Delete and restart the session."
    ),
    # Chunking
    ErrorCode.DS_201_CHUNK_TOO_LARGE: ("Reduce chunk size or split the file. File: {file_path}"),
    ErrorCode.DS_202_NO_CHUNKS_CREATED: (
        "Context produced zero chunks. Verify the files are not empty."
    ),
    ErrorCode.DS_203_AGGREGATION_CONFLICT: (
        "Sub-agents returned conflicting results. Review manually."
    ),
    ErrorCode.DS_204_RESULT_VALIDATION_FAILED: (
        "Sub-agent result failed schema validation. Chunk: {chunk_id}"
    ),
    ErrorCode.DS_205_BATCH_FAILED: (
        "Batch processing failed after retries. Try with --sequential flag."
    ),
    # Resource
    ErrorCode.DS_301_FILE_NOT_FOUND: ("Verify the file exists. Path: {file_path}"),
    ErrorCode.DS_302_PERMISSION_DENIED: ("Check file permissions. Path: {file_path}"),
    ErrorCode.DS_303_FILE_TOO_LARGE: (
        "Files larger than 10MB are skipped. Consider splitting the file. File: {file_path}"
    ),
    ErrorCode.DS_304_CONTEXT_TOO_LARGE: (
        "Total context exceeds 50MB. Reduce the number of files or use filtering."
    ),
    ErrorCode.DS_305_CACHE_DIR_ERROR: (
        "Cannot create or access cache directory. Check disk space and permissions."
    ),
    ErrorCode.DS_306_SESSION_NOT_FOUND: (
        "Use 'deepscan list' to see available sessions. Session: {session_id}"
    ),
    # Config
    ErrorCode.DS_401_INVALID_CONFIG_FILE: (
        "Config file has syntax errors. Validate with a YAML/JSON linter. File: {file_path}"
    ),
    ErrorCode.DS_402_MISSING_REQUIRED_SETTING: ("Required setting is missing from configuration."),
    ErrorCode.DS_403_INVALID_MODEL_SETTING: (
        "Supported models: haiku, sonnet. Check your model specification."
    ),
    ErrorCode.DS_404_ESCALATION_BUDGET_EXCEEDED: (
        "Model escalation budget exhausted. Increase max_escalation_ratio or max_sonnet_cost."
    ),
    # System
    ErrorCode.DS_501_INTERNAL_ERROR: ("An unexpected error occurred. Please report this issue."),
    ErrorCode.DS_502_STATE_CORRUPTION: (
        "Session state is corrupted. Delete the session and retry."
    ),
    ErrorCode.DS_503_TIMEOUT_ERROR: (
        "Operation timed out. Try increasing timeout or splitting the work."
    ),
    ErrorCode.DS_504_RATE_LIMIT_ERROR: (
        "API rate limit exceeded. Wait and retry, or reduce parallel agents."
    ),
    ErrorCode.DS_505_CANCELLED_BY_USER: ("Resume with 'deepscan --resume {session_id}'"),
}

DEFAULT_REMEDIATION = "No specific remediation available. Check documentation."


def get_remediation(code: ErrorCode, context: ErrorContext | None = None) -> str:
    """Get remediation suggestion for error code.

    Supports template strings with context placeholders.

    Args:
        code: The error code.
        context: Optional context for template substitution.

    Returns:
        Remediation hint string with context values filled in.
    """
    template = REMEDIATION_TEMPLATES.get(code, DEFAULT_REMEDIATION)

    if context is None:
        context = ErrorContext()

    # Build substitution dict with safe defaults for None values
    ctx_dict = context.model_dump()
    safe_dict = {
        k: (v if v is not None else f"<{k}>")
        for k, v in ctx_dict.items()
        if not isinstance(v, dict)
    }
    # Handle extra dict separately
    safe_dict.update(ctx_dict.get("extra", {}))

    try:
        return template.format(**safe_dict)
    except (KeyError, ValueError):
        # KeyError: Template has placeholders not in context
        # ValueError: Malformed template string (e.g., unclosed brace)
        # In either case, return raw template as safe fallback
        return template


# =============================================================================
# Exit Code Mapping
# =============================================================================

CATEGORY_EXIT_CODES: dict[ErrorCategory, int] = {
    ErrorCategory.VALIDATION: 2,  # Standard Unix misuse
    ErrorCategory.PARSING: 3,  # Data error
    ErrorCategory.CHUNKING: 4,  # Processing error
    ErrorCategory.RESOURCE: 5,  # File error
    ErrorCategory.CONFIG: 6,  # Config error
    ErrorCategory.SYSTEM: 1,  # General error
}


def get_exit_code(code: ErrorCode) -> int:
    """Map error code to Unix exit code.

    Special case: DS-505 (CANCELLED_BY_USER) returns 130,
    which is the Unix convention for SIGINT (128 + signal 2).
    This matches CANCELLATION.md specification (Issue P fix).

    Args:
        code: The error code.

    Returns:
        Unix exit code (0-255).
    """
    # Issue P Fix: DS-505 uses Unix convention for signal termination
    # 130 = 128 + SIGINT(2), consistent with CANCELLATION.md
    if code == ErrorCode.DS_505_CANCELLED_BY_USER:
        return 130

    return CATEGORY_EXIT_CODES.get(code.category, 1)


# =============================================================================
# Error Handler
# =============================================================================


def handle_error(error: DeepScanError, verbose: bool = False) -> int:
    """Handle DeepScanError and print formatted output.

    Uses Rich console for styled output when available.
    Security: Escapes user-controlled strings to prevent Rich markup injection.

    Args:
        error: The error to handle.
        verbose: Whether to show detailed output.

    Returns:
        Exit code for CLI.
    """
    import sys as sys_module

    # Try to import Rich with markup escape for security
    try:
        from rich.console import Console
        from rich.markup import escape as rich_escape

        console: Console | None = Console(stderr=True)
    except ImportError:
        console = None

        def rich_escape(x):
            return x  # No-op when Rich not available

    def emit(rich_msg: str, plain_msg: str) -> None:
        """Emit message to console (Rich) or stderr (plain)."""
        if console is not None:
            console.print(rich_msg)
        else:
            print(plain_msg, file=sys_module.stderr)

    # Resolve cause from explicit arg or Python's native exception chaining
    cause = error.cause or getattr(error, "__cause__", None)

    # Main error message (escape user-controlled content)
    safe_message = rich_escape(error.message)
    emit(
        f"[red bold]{error.code.code_str}[/] {error.code.title}",
        f"{error.code.code_str} {error.code.title}",
    )
    emit(f"  {safe_message}", f"  {error.message}")

    # Context details (escape file paths - could contain malicious characters)
    if error.context.file_path:
        safe_path = rich_escape(error.context.file_path)
        emit(f"  [dim]File:[/] {safe_path}", f"  File: {error.context.file_path}")

    # Verbose mode shows more
    if verbose:
        emit(
            f"\n[dim]Category:[/] {error.code.category.value}",
            f"\nCategory: {error.code.category.value}",
        )
        emit(
            f"[dim]Documentation:[/] {error.code.doc_url}",
            f"Documentation: {error.code.doc_url}",
        )
        if cause:
            cause_str = f"{type(cause).__name__}: {cause}"
            safe_cause = rich_escape(cause_str)
            emit(f"[dim]Caused by:[/] {safe_cause}", f"Caused by: {cause_str}")

    # Remediation hint (escape as it may contain user paths)
    remediation = get_remediation(error.code, error.context)
    if remediation and remediation != DEFAULT_REMEDIATION:
        safe_remediation = rich_escape(remediation)
        emit(
            f"\n[yellow]Suggestion:[/] {safe_remediation}",
            f"\nSuggestion: {remediation}",
        )

    # Return exit code based on category
    return get_exit_code(error.code)
