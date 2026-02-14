"""AST-based Semantic Chunking for DeepScan Phase 6.

Provides language-aware code chunking using tree-sitter for AST parsing.
Splits code at semantic boundaries (class, function, method) rather than
arbitrary character positions.

Key Features:
- Scope-Aware Chunking: Keeps functions, classes, methods whole
- Coalescing Iterator: Captures ALL content including gaps between nodes
- Graceful Fallback: Uses text-based chunking on parse errors
- Memory Management: Periodic gc.collect() for large codebases
- Security: Path traversal protection, recursion depth limits

Usage:
    from ast_chunker import chunk_file_ast, SemanticChunk

    chunks = chunk_file_ast(Path("src/main.py"), max_chunk_chars=150_000)
    for chunk in chunks:
        print(f"{chunk.node_type}: lines {chunk.start_line}-{chunk.end_line}")
"""

from __future__ import annotations

import gc
import hashlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    pass  # tree-sitter types for IDE support

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration Constants
# =============================================================================

# Scope types by language - nodes that define semantic boundaries
# Updated: Added decorated_definition for Python (Gemini feedback)
SCOPE_TYPES_BY_LANGUAGE: dict[str, set[str]] = {
    "python": {
        "module",
        "class_definition",
        "function_definition",
        "decorated_definition",  # Important: keeps decorators with functions
    },
    "javascript": {
        "program",
        "class_declaration",
        "function_declaration",
        "arrow_function",
        "method_definition",
    },
    "typescript": {
        "program",
        "class_declaration",
        "interface_declaration",  # TypeScript interfaces as semantic boundaries
        "function_declaration",
        "arrow_function",
        "method_definition",
    },
    "java": {
        "program",
        "class_declaration",
        "method_declaration",
        "constructor_declaration",
    },
    "go": {
        "source_file",
        "type_declaration",
        "function_declaration",
        "method_declaration",
    },
}

# Compound statements to keep as atomic units
COMPOUND_TYPES_BY_LANGUAGE: dict[str, set[str]] = {
    "python": {
        "if_statement",
        "for_statement",
        "while_statement",
        "try_statement",
        "with_statement",
        "match_statement",
    },
    "javascript": {
        "if_statement",
        "for_statement",
        "while_statement",
        "try_statement",
        "switch_statement",
    },
    "typescript": {
        "if_statement",
        "for_statement",
        "while_statement",
        "try_statement",
        "switch_statement",
    },
    "java": {
        "if_statement",
        "for_statement",
        "while_statement",
        "try_statement",
        "switch_expression",
    },
    "go": {
        "if_statement",
        "for_statement",
        "select_statement",
        "switch_statement",
    },
}

# Language detection by file extension
LANGUAGE_BY_EXTENSION: dict[str, str] = {
    ".py": "python",
    ".pyw": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
}

# Memory management configuration
GC_EVERY_N_FILES = 50
MEMORY_THRESHOLD_MB = 500
MIN_FILES_FOR_MEMORY_GC = 10  # Minimum files before memory-pressure GC (prevents thrashing)

# Token estimation safety margin (80% utilization per vibe_check/Gemini advice)
TOKEN_SAFETY_MARGIN = 0.80


# =============================================================================
# Data Models
# =============================================================================


class SemanticChunk(BaseModel):
    """A semantically meaningful code chunk.

    Attributes:
        chunk_id: Deterministic ID (NOT random) for caching compatibility.
        content: The actual code content.
        start_line: 1-based starting line number.
        end_line: 1-based ending line number.
        node_type: AST node type (e.g., "function_definition", "gap_content").
        language: Programming language (e.g., "python", "javascript").
        file_path: Source file path (relative for cache portability).
        char_count: Character count (auto-calculated).
        token_count: Estimated token count (auto-calculated).
        is_fallback: True if text-based split was used instead of AST.
    """

    chunk_id: str = Field(default="pending")
    content: str
    start_line: int
    end_line: int
    node_type: str
    language: str
    file_path: str | None = None

    # Metadata (auto-calculated)
    char_count: int = 0
    token_count: int = 0
    is_fallback: bool = False

    def model_post_init(self, __context: Any) -> None:
        """Calculate char_count and token_count after model creation."""
        self.char_count = len(self.content)
        self.token_count = count_tokens(self.content)

    @classmethod
    def with_deterministic_id(
        cls,
        file_path: str,
        start_line: int,
        content: str,
        **kwargs: Any,
    ) -> SemanticChunk:
        """Factory method that creates chunk with deterministic ID.

        Args:
            file_path: Source file path (use relative for portability).
            start_line: Starting line number.
            content: Chunk content.
            **kwargs: Additional fields (end_line, node_type, language, etc.).

        Returns:
            SemanticChunk with deterministic chunk_id.
        """
        chunk_id = generate_chunk_id(file_path, start_line, content)
        return cls(
            chunk_id=chunk_id,
            content=content,
            start_line=start_line,
            file_path=file_path,
            **kwargs,
        )


# =============================================================================
# Utility Functions
# =============================================================================


def detect_language(file_path: Path) -> str | None:
    """Detect programming language from file extension.

    Args:
        file_path: Path to the source file.

    Returns:
        Language name (e.g., "python") or None if unknown.
    """
    ext = file_path.suffix.lower()
    return LANGUAGE_BY_EXTENSION.get(ext)


def count_tokens(text: str) -> int:
    """Estimate token count for text.

    Uses character-based estimation with language-aware adjustments.
    Returns RAW estimate - safety margin (TOKEN_SAFETY_MARGIN) is applied
    by the caller (extract_scopes_v2) when comparing against limits.

    Args:
        text: The text to count tokens for.

    Returns:
        Estimated token count (raw, without safety margin).
    """
    if not text:
        return 0

    # Base estimate: ~4 characters per token for code
    base_estimate = len(text) // 4

    # Adjust for whitespace-heavy content (indentation)
    whitespace_ratio = sum(1 for c in text if c.isspace()) / max(len(text), 1)
    if whitespace_ratio > 0.3:
        # Heavily indented code has fewer tokens per character
        base_estimate = int(base_estimate * 0.8)

    return max(1, base_estimate)


def generate_chunk_id(file_path: str, start_line: int, content: str) -> str:
    """Generate deterministic chunk ID.

    Uses hash of file path + start line + full content to ensure
    same input always produces same ID (required for Phase 5 caching).

    Note: Uses relative path format for cache portability across machines.
    Updated: Uses incremental hashing to avoid memory spikes on large chunks.

    Args:
        file_path: Source file path (preferably relative).
        start_line: Starting line number.
        content: Chunk content.

    Returns:
        8-character hex ID.
    """
    # Incremental hashing to avoid memory spike from f-string concatenation
    sha = hashlib.sha256()
    sha.update(file_path.encode("utf-8"))
    sha.update(b":")
    sha.update(str(start_line).encode("utf-8"))
    sha.update(b":")
    sha.update(content.encode("utf-8"))
    return sha.hexdigest()[:8]


def get_line_number(content: bytes, byte_offset: int) -> int:
    """Get 1-based line number for a byte offset.

    .. deprecated::
        This function has O(N) complexity per call. For batch processing,
        use AST node attributes (node.start_point, node.end_point) instead,
        which provide O(1) access to line numbers. This function is retained
        for backward compatibility and edge cases in fallback text chunking.

    Args:
        content: Full file content as bytes.
        byte_offset: Byte position in the content.

    Returns:
        1-based line number.
    """
    return content[:byte_offset].count(b"\n") + 1


def split_text_lines(text: str, max_chars: int) -> list[str]:
    """Split text at line boundaries respecting max_chars.

    Args:
        text: Text to split.
        max_chars: Maximum characters per chunk.

    Returns:
        List of text chunks.
    """
    lines = text.splitlines(keepends=True)
    chunks: list[str] = []
    current_chunk: list[str] = []
    current_size = 0

    for line in lines:
        if current_size + len(line) > max_chars and current_chunk:
            chunks.append("".join(current_chunk))
            current_chunk = [line]
            current_size = len(line)
        else:
            current_chunk.append(line)
            current_size += len(line)

    if current_chunk:
        chunks.append("".join(current_chunk))

    return chunks


def get_parser_safe(language: str) -> Any | None:
    """Safely get tree-sitter parser with import guard.

    Supports both tree-sitter-language-pack (Python 3.13+) and
    tree-sitter-languages (Python 3.12 and earlier).

    Returns None if neither package is available,
    allowing graceful fallback to text-based chunking.

    Args:
        language: Programming language name.

    Returns:
        Parser instance or None if unavailable.
    """
    # Try tree-sitter-language-pack first (maintained, Python 3.13 support)
    try:
        from tree_sitter_language_pack import get_parser

        parser = get_parser(language)
        return parser
    except ImportError:
        pass  # Try fallback
    except Exception as e:
        logger.debug(f"tree-sitter-language-pack failed for {language}: {e}")

    # Fallback to tree-sitter-languages (legacy, Python 3.12 and earlier)
    try:
        from tree_sitter_languages import get_parser

        parser = get_parser(language)
        return parser
    except ImportError:
        logger.warning(
            "No tree-sitter package available. Install with: poetry add tree-sitter-language-pack"
        )
        return None
    except Exception as e:
        logger.warning(f"Failed to get parser for {language}: {e}")
        return None


# =============================================================================
# Core Chunking Functions
# =============================================================================


def chunk_file_ast(
    file_path: Path,
    max_chunk_chars: int = 150_000,
    max_chunk_tokens: int = 40_000,
    max_depth: int = 50,
    project_root: Path | None = None,
) -> list[SemanticChunk]:
    """AST-based semantic chunking with Coalescing Iterator.

    Main entry point for semantic chunking. Parses the file with tree-sitter
    and extracts chunks at semantic boundaries (functions, classes, etc.).

    Args:
        file_path: Source file to chunk.
        max_chunk_chars: Character limit per chunk.
        max_chunk_tokens: Token limit per chunk (safety).
        max_depth: Maximum recursion depth (DoS protection).
        project_root: Project root for relative path calculation.

    Returns:
        List of SemanticChunk objects.
    """
    # 1. Validate file path (Security Fix S1 - Path Traversal)
    try:
        resolved_path = file_path.resolve(strict=True)
    except (OSError, RuntimeError) as e:
        logger.error(f"Invalid file path {file_path}: {e}")
        return []

    # Check for path traversal (file should exist and be readable)
    if not resolved_path.is_file():
        logger.error(f"Not a file: {file_path}")
        return []

    # Security: Enforce file is within project_root if provided (code review fix)
    if project_root:
        try:
            resolved_root = project_root.resolve()
            resolved_path.relative_to(resolved_root)
        except ValueError:
            logger.error(f"Security: {file_path} is outside project root {project_root}")
            return []

    # 2. Detect language and get parser
    language = detect_language(resolved_path)
    if not language:
        logger.info(f"Unknown language for {file_path}, using text fallback")
        return fallback_text_chunk(resolved_path, max_chunk_chars, project_root)

    parser = get_parser_safe(language)
    if parser is None:
        logger.warning(f"Parser unavailable for {language}, using text fallback")
        return fallback_text_chunk(resolved_path, max_chunk_chars, project_root)

    # 3. Parse file
    try:
        content = resolved_path.read_bytes()
        tree = parser.parse(content)
    except Exception as e:
        logger.warning(f"AST parse failed for {file_path}: {e}")
        return fallback_text_chunk(resolved_path, max_chunk_chars, project_root)

    # 4. Calculate relative path for chunk IDs (portability)
    if project_root:
        try:
            rel_path = str(resolved_path.relative_to(project_root))
        except ValueError:
            rel_path = resolved_path.name
    else:
        rel_path = resolved_path.name

    # 5. Coalescing Iterator extraction
    chunks: list[SemanticChunk] = []
    extract_scopes_v2(
        node=tree.root_node,
        content=content,
        chunks=chunks,
        max_chars=max_chunk_chars,
        max_tokens=max_chunk_tokens,
        language=language,
        file_path=rel_path,
        depth=0,
        max_depth=max_depth,
    )

    # 6. Cleanup tree (memory management)
    del tree

    # 7. Assign deterministic chunk IDs
    for chunk in chunks:
        if chunk.chunk_id == "pending":
            chunk.chunk_id = generate_chunk_id(
                file_path=rel_path,
                start_line=chunk.start_line,
                content=chunk.content,
            )

    return chunks


def extract_scopes_v2(
    node: Any,
    content: bytes,
    chunks: list[SemanticChunk],
    max_chars: int,
    max_tokens: int,
    language: str,
    file_path: str,
    depth: int = 0,
    max_depth: int = 50,
    last_byte: int = 0,
) -> int:
    """Coalescing Iterator: captures ALL content including gaps.

    This algorithm ensures no content is lost by:
    1. Tracking the last processed byte position
    2. Capturing gaps between child nodes
    3. Including non-scope content (imports, constants)
    4. Handling compound statements as atomic units
    5. Treating ERROR nodes as leaf content (graceful degradation)

    Args:
        node: Current AST node.
        content: Full file content as bytes.
        chunks: Output list of chunks.
        max_chars: Maximum characters per chunk.
        max_tokens: Maximum tokens per chunk.
        language: Programming language.
        file_path: Source file path (for chunk IDs).
        depth: Current recursion depth.
        max_depth: Maximum recursion depth (DoS protection).
        last_byte: Last processed byte position.

    Returns:
        Last processed byte position after this node.
    """
    # Apply token safety margin (80% utilization to prevent context overflow)
    effective_max_tokens = int(max_tokens * TOKEN_SAFETY_MARGIN)

    # Security: Prevent deep recursion (Issue S2)
    if depth > max_depth:
        logger.warning(f"Max recursion depth {max_depth} reached, using text fallback")
        node_text = content[node.start_byte : node.end_byte].decode("utf-8", errors="replace")

        # Check if node is too large even for fallback
        if len(node_text) > max_chars:
            text_chunks = split_text_lines(node_text, max_chars)
            base_line = node.start_point[0] + 1
            current_line_offset = 0

            for tc in text_chunks:
                chunk_line_count = tc.count("\n")
                chunks.append(
                    SemanticChunk(
                        content=tc,
                        start_line=base_line + current_line_offset,
                        end_line=base_line + current_line_offset + chunk_line_count,
                        node_type="depth_limit_split",
                        language=language,
                        file_path=file_path,
                        is_fallback=True,
                    )
                )
                current_line_offset += chunk_line_count
        else:
            chunks.append(
                SemanticChunk(
                    content=node_text,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    node_type="depth_limit_fallback",
                    language=language,
                    file_path=file_path,
                    is_fallback=True,
                )
            )
        return node.end_byte

    scope_types = SCOPE_TYPES_BY_LANGUAGE.get(language, set())
    compound_types = COMPOUND_TYPES_BY_LANGUAGE.get(language, set())

    # Track position within this node
    current_byte = node.start_byte if last_byte < node.start_byte else last_byte

    # Issue X Fix: Track line position using AST node attributes instead of O(N) byte scanning
    # node.start_point is (row, col) where row is 0-indexed
    current_line_tracker = node.start_point[0] + 1

    for child in node.children:
        # 1. CAPTURE GAP before this child
        if child.start_byte > current_byte:
            gap_text = content[current_byte : child.start_byte].decode("utf-8", errors="replace")
            if gap_text.strip():  # Non-empty gap
                # Issue X Fix: Use tracked line position instead of O(N) get_line_number()
                gap_start_line = current_line_tracker
                gap_end_line = child.start_point[0] + 1

                if len(gap_text) > max_chars:
                    # Large gap - split
                    gap_chunks = split_text_lines(gap_text, max_chars)
                    base_line = gap_start_line  # Use tracked position
                    current_line_offset = 0

                    for gc_chunk in gap_chunks:
                        chunk_line_count = gc_chunk.count("\n")
                        chunks.append(
                            SemanticChunk(
                                content=gc_chunk,
                                start_line=base_line + current_line_offset,
                                end_line=base_line + current_line_offset + chunk_line_count,
                                node_type="gap_split",
                                language=language,
                                file_path=file_path,
                                is_fallback=True,
                            )
                        )
                        current_line_offset += chunk_line_count
                else:
                    chunks.append(
                        SemanticChunk(
                            content=gap_text,
                            start_line=gap_start_line,  # Use tracked position
                            end_line=gap_end_line,  # Use AST node attribute
                            node_type="gap_content",
                            language=language,
                            file_path=file_path,
                        )
                    )

        # 2. PROCESS this child
        child_text = content[child.start_byte : child.end_byte].decode("utf-8", errors="replace")
        child_tokens = count_tokens(child_text)
        child_chars = len(child_text)

        # Check node type
        is_scope = child.type in scope_types
        is_compound = child.type in compound_types
        is_error = child.type == "ERROR"

        # Handle ERROR nodes (Gemini feedback: treat as leaf content)
        if is_error:
            if child_chars <= max_chars:
                chunks.append(
                    SemanticChunk(
                        content=child_text,
                        start_line=child.start_point[0] + 1,
                        end_line=child.end_point[0] + 1,
                        node_type="syntax_error_block",
                        language=language,
                        file_path=file_path,
                        is_fallback=True,
                    )
                )
            else:
                # Large error block - text split
                text_chunks = split_text_lines(child_text, max_chars)
                base_line = child.start_point[0] + 1
                current_line_offset = 0

                for tc in text_chunks:
                    chunk_line_count = tc.count("\n")
                    chunks.append(
                        SemanticChunk(
                            content=tc,
                            start_line=base_line + current_line_offset,
                            end_line=base_line + current_line_offset + chunk_line_count,
                            node_type="syntax_error_split",
                            language=language,
                            file_path=file_path,
                            is_fallback=True,
                        )
                    )
                    current_line_offset += chunk_line_count
            current_byte = child.end_byte
            continue

        if is_scope or is_compound:
            if child_chars <= max_chars and child_tokens <= effective_max_tokens:
                # Whole scope/compound fits - add as single chunk
                chunks.append(
                    SemanticChunk(
                        content=child_text,
                        start_line=child.start_point[0] + 1,
                        end_line=child.end_point[0] + 1,
                        node_type=child.type,
                        language=language,
                        file_path=file_path,
                    )
                )
            else:
                # Too big - recurse into this scope/compound
                extract_scopes_v2(
                    node=child,
                    content=content,
                    chunks=chunks,
                    max_chars=max_chars,
                    max_tokens=max_tokens,
                    language=language,
                    file_path=file_path,
                    depth=depth + 1,
                    max_depth=max_depth,
                    last_byte=child.start_byte,
                )
        else:
            # Non-scope content (imports, constants, etc.)
            if child_chars <= max_chars:
                chunks.append(
                    SemanticChunk(
                        content=child_text,
                        start_line=child.start_point[0] + 1,
                        end_line=child.end_point[0] + 1,
                        node_type=child.type,
                        language=language,
                        file_path=file_path,
                    )
                )
            else:
                # Large non-scope content - use text split
                text_chunks = split_text_lines(child_text, max_chars)
                base_line = child.start_point[0] + 1
                current_line_offset = 0

                for tc in text_chunks:
                    chunk_line_count = tc.count("\n")
                    chunks.append(
                        SemanticChunk(
                            content=tc,
                            start_line=base_line + current_line_offset,
                            end_line=base_line + current_line_offset + chunk_line_count,
                            node_type="text_split",
                            language=language,
                            file_path=file_path,
                            is_fallback=True,
                        )
                    )
                    current_line_offset += chunk_line_count

        current_byte = child.end_byte
        # Issue X Fix: Update line tracker using AST node attribute (O(1))
        current_line_tracker = child.end_point[0] + 1

    # 3. CAPTURE trailing content after last child
    if node.end_byte > current_byte:
        trailing = content[current_byte : node.end_byte].decode("utf-8", errors="replace")
        if trailing.strip():
            # Issue X Fix: Use tracked line position instead of O(N) get_line_number()
            trailing_start_line = current_line_tracker
            trailing_end_line = node.end_point[0] + 1

            if len(trailing) > max_chars:
                text_chunks = split_text_lines(trailing, max_chars)
                base_line = trailing_start_line  # Use tracked position
                current_line_offset = 0

                for tc in text_chunks:
                    chunk_line_count = tc.count("\n")
                    chunks.append(
                        SemanticChunk(
                            content=tc,
                            start_line=base_line + current_line_offset,
                            end_line=base_line + current_line_offset + chunk_line_count,
                            node_type="trailing_split",
                            language=language,
                            file_path=file_path,
                            is_fallback=True,
                        )
                    )
                    current_line_offset += chunk_line_count
            else:
                chunks.append(
                    SemanticChunk(
                        content=trailing,
                        start_line=trailing_start_line,  # Use tracked position
                        end_line=trailing_end_line,
                        node_type="trailing_content",
                        language=language,
                        file_path=file_path,
                    )
                )

    return node.end_byte


def fallback_text_chunk(
    file_path: Path,
    max_chunk_chars: int,
    project_root: Path | None = None,
    overlap_lines_count: int = 5,
) -> list[SemanticChunk]:
    """Text-based chunking fallback.

    Uses line-aware splitting to avoid mid-line breaks.
    Includes overlap between chunks for context preservation.

    Args:
        file_path: Source file path.
        max_chunk_chars: Maximum characters per chunk.
        project_root: Project root for relative path calculation.
        overlap_lines_count: Number of lines to overlap between chunks.

    Returns:
        List of SemanticChunk objects.
    """
    # Validate path (Security Fix S1)
    try:
        resolved_path = file_path.resolve(strict=True)
    except (OSError, RuntimeError) as e:
        logger.error(f"Invalid file path {file_path}: {e}")
        return []

    if not resolved_path.is_file():
        logger.error(f"Not a file: {file_path}")
        return []

    try:
        content = resolved_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        logger.error(f"Failed to read {file_path}: {e}")
        return []

    lines = content.splitlines(keepends=True)
    if not lines:
        return []

    # Calculate relative path
    if project_root:
        try:
            rel_path = str(resolved_path.relative_to(project_root))
        except ValueError:
            rel_path = resolved_path.name
    else:
        rel_path = resolved_path.name

    # Detect language for metadata
    language = detect_language(resolved_path) or "unknown"

    chunks: list[SemanticChunk] = []
    current_chunk: list[str] = []
    current_size = 0
    start_line = 1  # 1-based line numbers

    for i, line in enumerate(lines):
        line_number = i + 1  # Convert to 1-based

        if current_size + len(line) > max_chunk_chars and current_chunk:
            # Save current chunk
            chunk_content = "".join(current_chunk)
            chunks.append(
                SemanticChunk.with_deterministic_id(
                    file_path=rel_path,
                    start_line=start_line,
                    content=chunk_content,
                    end_line=line_number - 1,
                    node_type="text_fallback",
                    language=language,
                    is_fallback=True,
                )
            )

            # Start new chunk with overlap
            overlap_lines = (
                current_chunk[-overlap_lines_count:]
                if len(current_chunk) >= overlap_lines_count
                else current_chunk[:]
            )
            current_chunk = overlap_lines + [line]
            current_size = sum(len(ln) for ln in current_chunk)

            # Calculate new start line
            start_line = max(1, line_number - len(overlap_lines))
        else:
            current_chunk.append(line)
            current_size += len(line)

    # Final chunk
    if current_chunk:
        chunk_content = "".join(current_chunk)
        chunks.append(
            SemanticChunk.with_deterministic_id(
                file_path=rel_path,
                start_line=start_line,
                content=chunk_content,
                end_line=len(lines),
                node_type="text_fallback",
                language=language,
                is_fallback=True,
            )
        )

    return chunks


from collections.abc import Iterator  # noqa: E402


def chunk_files_safely(
    file_paths: list[Path],
    max_chunk_chars: int = 150_000,
    gc_interval: int = GC_EVERY_N_FILES,
    memory_threshold_mb: int = MEMORY_THRESHOLD_MB,
    project_root: Path | None = None,
) -> Iterator[SemanticChunk]:
    """Process files with optimized memory cleanup (generator version).

    Memory management strategy:
    1. Yields chunks immediately (no memory accumulation) - code review fix
    2. gc.collect() every N files (not every file!)
    3. Optional: trigger GC on memory pressure (with minimum interval to prevent thrashing)
    4. Tree objects are deleted immediately after use

    Args:
        file_paths: List of files to process.
        max_chunk_chars: Maximum characters per chunk.
        gc_interval: Run gc.collect() every N files (default: 50).
        memory_threshold_mb: Trigger GC if memory exceeds this (MB).
        project_root: Project root for relative path calculation.

    Yields:
        SemanticChunk objects as they are created.
    """
    # Import psutil once at function start (not in loop)
    try:
        import psutil

        _psutil_available = True
        _process = psutil.Process()
    except ImportError:
        _psutil_available = False
        _process = None

    files_since_gc = 0

    for i, file_path in enumerate(file_paths):
        # Parse and chunk
        chunks = chunk_file_ast(file_path, max_chunk_chars, project_root=project_root)
        # Yield immediately instead of accumulating (memory optimization)
        yield from chunks
        files_since_gc += 1

        # Determine if GC is needed
        should_gc = False

        # Strategy 1: Interval-based
        if files_since_gc >= gc_interval:
            should_gc = True

        # Strategy 2: Memory pressure (requires minimum file interval to prevent thrashing)
        if _psutil_available and _process and files_since_gc >= MIN_FILES_FOR_MEMORY_GC:
            try:
                memory_mb = _process.memory_info().rss / (1024 * 1024)
                if memory_mb > memory_threshold_mb:
                    should_gc = True
                    logger.debug(f"Memory pressure detected: {memory_mb:.1f}MB")
            except Exception:
                pass  # Error checking memory

        if should_gc:
            gc.collect()
            files_since_gc = 0
            logger.debug(f"GC triggered after {i + 1} files")

    # Final cleanup
    gc.collect()


def chunk_files_to_list(
    file_paths: list[Path],
    max_chunk_chars: int = 150_000,
    gc_interval: int = GC_EVERY_N_FILES,
    memory_threshold_mb: int = MEMORY_THRESHOLD_MB,
    project_root: Path | None = None,
) -> list[SemanticChunk]:
    """Convenience wrapper that returns a list instead of generator.

    Warning: This accumulates all chunks in memory. For large codebases,
    prefer using chunk_files_safely() generator directly.

    Args:
        file_paths: List of files to process.
        max_chunk_chars: Maximum characters per chunk.
        gc_interval: Run gc.collect() every N files.
        memory_threshold_mb: Trigger GC if memory exceeds this.
        project_root: Project root for relative path calculation.

    Returns:
        List of all SemanticChunk objects.
    """
    return list(
        chunk_files_safely(
            file_paths,
            max_chunk_chars,
            gc_interval,
            memory_threshold_mb,
            project_root,
        )
    )


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    # Data models
    "SemanticChunk",
    # Constants
    "SCOPE_TYPES_BY_LANGUAGE",
    "COMPOUND_TYPES_BY_LANGUAGE",
    "LANGUAGE_BY_EXTENSION",
    "TOKEN_SAFETY_MARGIN",
    "MIN_FILES_FOR_MEMORY_GC",
    # Core functions
    "chunk_file_ast",
    "fallback_text_chunk",
    "chunk_files_safely",
    "chunk_files_to_list",
    # Utilities
    "detect_language",
    "count_tokens",
    "generate_chunk_id",
    "get_parser_safe",
    "get_line_number",
    "split_text_lines",
]
