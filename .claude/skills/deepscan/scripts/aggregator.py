"""Result aggregation for DeepScan REDUCE phase.

Implements ARCH_05 §6: ResultAggregator for merging findings from multiple chunks.
Handles deduplication, contradiction detection, and confidence scoring.
"""

from __future__ import annotations

__all__ = [
    # Main class
    "ResultAggregator",
    # Enums
    "FinalMarkerType",
    # Data Models
    "ParsedFinalMarker",
    # Utility functions
    "aggregate_chunk_results",
    "parse_final_markers",
    "extract_final_answer",
    "has_final_marker",
]

from collections import defaultdict
from difflib import SequenceMatcher
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models import ChunkResult, Finding


class ResultAggregator:
    """Aggregates findings from multiple chunks (REDUCE phase).

    Algorithm:
    1. Collect all findings from all chunks
    2. Group by semantic similarity (deduplication)
    3. Merge similar findings (keep highest confidence)
    4. Sort by relevance to original query
    5. Flag contradictions for manual review

    Usage:
        aggregator = ResultAggregator(similarity_threshold=0.7)
        result = aggregator.aggregate_findings(chunk_results, query)
    """

    def __init__(self, similarity_threshold: float = 0.7):
        """Initialize aggregator.

        Args:
            similarity_threshold: Threshold for considering two findings similar.
                Higher values = stricter matching (less deduplication).
                Lower values = looser matching (more deduplication).
                Default: 0.7 (REQ_02 FR-006)
        """
        self.similarity_threshold = similarity_threshold

    def aggregate_findings(
        self,
        chunk_results: list[ChunkResult],
        original_query: str,
        deleted_files: list[str] | None = None,
    ) -> dict:
        """Aggregate findings from all chunks.

        Args:
            chunk_results: List of ChunkResult objects from processed chunks.
            original_query: Original user query for relevance scoring.
            deleted_files: Optional list of deleted file paths to filter out
                (P7-003: Ghost Findings Cleanup).

        Returns:
            Dict containing:
            - aggregated_findings: Merged and deduplicated findings
            - total_findings: Original count before deduplication (post-filter)
            - unique_findings: Count after deduplication
            - deduplication_ratio: Percentage of duplicates removed
            - contradictions: List of detected contradictory findings
            - needs_manual_review: True if contradictions exist
            - filtered_deleted_files: Count of findings filtered due to deleted files
        """
        # Normalize deleted files paths (P7-003)
        deleted_set = self._normalize_deleted_paths(deleted_files)
        filtered_count = 0

        # Step 1: Collect all findings (with ghost filter)
        all_findings = []
        verification_count = 0
        for result in chunk_results:
            for finding in result.findings:
                # P7-003: Filter findings from deleted files
                if deleted_set and self._is_ghost_finding(finding, result.chunk_id, deleted_set):
                    filtered_count += 1
                    continue

                # P3.3-FIX: Parse NEEDS_VERIFICATION prefix
                # Issue 6 FIX: Handle prefix with or without colon (prompt/parser mismatch)
                point = finding.point
                needs_verification = finding.verification_required
                if point.startswith("NEEDS_VERIFICATION"):
                    needs_verification = True
                    verification_count += 1
                    # Remove prefix, handling optional colon and whitespace
                    point = point[len("NEEDS_VERIFICATION"):].lstrip(": ").strip()

                all_findings.append(
                    {
                        "finding": finding,
                        "source_chunk": result.chunk_id,
                        "confidence": finding.confidence,
                        "point_clean": point,  # Cleaned point without prefix
                        "verification_required": needs_verification,
                    }
                )

        if not all_findings:
            return {
                "aggregated_findings": [],
                "total_findings": 0,
                "unique_findings": 0,
                "deduplication_ratio": 0.0,
                "contradictions": [],
                "needs_manual_review": False,
                "filtered_deleted_files": filtered_count,
                "verification_required_count": 0,  # P3.3-FIX
                "verification_required_findings": [],  # P3.3-FIX
            }

        # Step 2: Group by similarity
        groups = self._group_by_similarity(all_findings)

        # Step 3: Merge similar findings
        merged = []
        for group in groups:
            best = max(group, key=lambda x: self._confidence_score(x["confidence"]))
            # P3.3-FIX: Preserve verification_required flag (OR logic - if ANY needs it)
            verification_required = any(f.get("verification_required", False) for f in group)
            merged.append(
                {
                    "finding": best["finding"],
                    "sources": [f["source_chunk"] for f in group],
                    "support_count": len(group),
                    "confidence": best["confidence"],
                    "verification_required": verification_required,
                    # Issue 5 FIX: Store cleaned point to avoid redundant stripping
                    "point_clean": best["point_clean"],
                }
            )

        # Step 4: Sort by relevance
        merged.sort(key=lambda x: -self._relevance_score(x["finding"], original_query))

        # Step 5: Detect contradictions
        contradictions = self._detect_contradictions(merged)

        # P3.3-FIX: Separate verification-required findings for distinct display
        verification_findings = [f for f in merged if f.get("verification_required", False)]

        return {
            "aggregated_findings": merged,
            "total_findings": len(all_findings),
            "unique_findings": len(merged),
            "deduplication_ratio": 1 - (len(merged) / max(len(all_findings), 1)),
            "contradictions": contradictions,
            "needs_manual_review": len(contradictions) > 0,
            "filtered_deleted_files": filtered_count,
            "verification_required_count": len(verification_findings),  # P3.3-FIX
            "verification_required_findings": verification_findings,  # P3.3-FIX
        }

    def _normalize_deleted_paths(self, deleted_files: list[str] | None) -> set[str]:
        """Normalize deleted file paths for comparison.

        Converts backslashes to forward slashes for cross-platform matching.

        Args:
            deleted_files: List of deleted file paths, or None.

        Returns:
            Set of normalized paths (lowercase, forward slashes).
        """
        if not deleted_files:
            return set()

        return {self._normalize_path(p) for p in deleted_files}

    def _normalize_path(self, path: str) -> str:
        """Normalize a single path for comparison.

        Args:
            path: File path string.

        Returns:
            Normalized path (forward slashes, lowercase).
        """
        # Replace backslashes with forward slashes, lowercase
        return path.replace("\\", "/").lower()

    def _is_ghost_finding(
        self,
        finding: Finding,
        chunk_id: str,
        deleted_paths: set[str],
    ) -> bool:
        """Check if a finding references a deleted file.

        Checks multiple sources:
        1. chunk_id (may contain file path)
        2. finding.location.file (if present)
        3. finding.evidence (may mention file name)

        Args:
            finding: Finding object to check.
            chunk_id: Chunk identifier (may contain file path).
            deleted_paths: Set of normalized deleted file paths.

        Returns:
            True if finding references a deleted file.
        """
        # Check chunk_id
        chunk_norm = self._normalize_path(chunk_id)
        for deleted in deleted_paths:
            if deleted in chunk_norm:
                return True

        # Check finding.location.file
        if finding.location and "file" in finding.location:
            loc_file = self._normalize_path(str(finding.location["file"]))
            for deleted in deleted_paths:
                if deleted in loc_file:
                    return True

        # Check finding.evidence (may mention file path)
        if finding.evidence:
            evidence_norm = self._normalize_path(finding.evidence)
            for deleted in deleted_paths:
                if deleted in evidence_norm:
                    return True

        return False

    def _group_by_similarity(self, findings: list[dict]) -> list[list[dict]]:
        """Group findings by text similarity with token-based blocking optimization.

        Optimized algorithm:
        1. Build inverted index by tokens (O(n))
        2. For each finding, only compare against candidates sharing tokens
        3. Apply quick filters (length ratio, token overlap) before expensive similarity
        4. Use greedy grouping within candidate set

        Complexity: O(n * k + b^2 * m) where k=avg tokens, b=avg block size, m=string length
        For diverse natural language, b << n, so effectively near-linear.
        Worst case (all findings share words): Still O(n^2) but rare for real data.

        Args:
            findings: List of finding dicts with 'finding' key.

        Returns:
            List of groups (each group is a list of finding dicts).
        """
        if len(findings) <= 1:
            return [[f] for f in findings]

        groups = []
        used = set()

        # Build token index for blocking - O(n)
        token_index = self._build_token_index(findings)

        for i, f1 in enumerate(findings):
            if i in used:
                continue

            group = [f1]
            used.add(i)
            # Issue 2 FIX: Use point_clean to exclude NEEDS_VERIFICATION prefix from similarity
            text1 = f1["point_clean"]

            # Get candidate indices from token index (only findings sharing tokens)
            candidates = set()
            words = text1.lower().split()[:5]
            for word in words:
                if len(word) >= 3:
                    candidates.update(token_index.get(word, []))
            candidates.discard(i)
            candidates -= used

            for j in candidates:
                f2 = findings[j]
                # Issue 2 FIX: Use point_clean for consistent deduplication
                text2 = f2["point_clean"]

                # Quick filter before expensive SequenceMatcher
                if not self._can_be_similar(text1, text2):
                    continue

                # Full similarity check
                similarity = self._text_similarity(text1, text2)
                if similarity >= self.similarity_threshold:
                    group.append(f2)
                    used.add(j)

            groups.append(group)

        return groups

    def _text_similarity(self, a: str, b: str) -> float:
        """Calculate text similarity using SequenceMatcher.

        Args:
            a: First text.
            b: Second text.

        Returns:
            Similarity ratio (0.0 to 1.0).
        """
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def _can_be_similar(self, a: str, b: str) -> bool:
        """Quick check if two strings could possibly be similar.

        Uses length ratio and token overlap as fast filters before
        expensive SequenceMatcher computation.

        Args:
            a: First text.
            b: Second text.

        Returns:
            True if strings could be similar (needs full check),
            False if definitely not similar.
        """
        len_a, len_b = len(a), len(b)
        if len_a == 0 or len_b == 0:
            return len_a == len_b  # Both empty = similar

        # Length ratio check - strings with very different lengths can't be similar
        # Use 0.5 as absolute minimum (more lenient than similarity_threshold)
        # because SequenceMatcher can still find high similarity with length differences
        length_ratio = min(len_a, len_b) / max(len_a, len_b)
        if length_ratio < 0.5:
            return False

        # Quick token overlap check - no shared words = definitely not similar
        tokens_a = set(a.lower().split()[:5])
        tokens_b = set(b.lower().split()[:5])
        if tokens_a and tokens_b and not (tokens_a & tokens_b):
            return False

        return True

    def _build_token_index(self, findings: list[dict]) -> dict[str, list[int]]:
        """Build inverted index of findings by significant tokens.

        Enables token-based blocking for O(n) index build instead of O(n^2) comparisons.

        Args:
            findings: List of finding dicts with 'finding' key.

        Returns:
            Dict mapping tokens to list of finding indices.
        """
        token_index: dict[str, list[int]] = defaultdict(list)

        for i, f in enumerate(findings):
            # Issue 2 FIX: Use point_clean for consistent token indexing
            text = f["point_clean"].lower()
            words = text.split()[:5]  # First 5 words
            for word in words:
                if len(word) >= 3:  # Skip very short words (articles, etc.)
                    token_index[word].append(i)

        return token_index

    def _confidence_score(self, confidence: str) -> int:
        """Convert confidence level to numeric score.

        Args:
            confidence: 'high', 'medium', or 'low' (case-insensitive).

        Returns:
            Numeric score (3, 2, or 1). Unknown values return 1 (same as 'low').
        """
        # Normalize to lowercase for case-insensitive matching
        normalized = confidence.lower() if confidence else ""
        # Return 1 (low) for unknown values instead of 0 to avoid unexpected ordering
        return {"high": 3, "medium": 2, "low": 1}.get(normalized, 1)

    def _relevance_score(self, finding: Finding, query: str) -> float:
        """Calculate relevance to original query.

        Uses simple keyword overlap scoring.

        Args:
            finding: Finding object.
            query: Original query string.

        Returns:
            Relevance score (0.0 to 1.0).
        """
        query_words = set(query.lower().split())
        finding_words = set(finding.point.lower().split())

        if not query_words:
            return 1.0

        overlap = len(query_words & finding_words)
        return overlap / len(query_words)

    def _detect_contradictions(self, merged: list[dict]) -> list[dict]:
        """Detect contradictory findings with early termination optimization.

        Simple heuristic: looks for negation patterns in similar findings.
        Optimized with length ratio filter to reduce SequenceMatcher calls.

        Args:
            merged: List of merged finding dicts.

        Returns:
            List of contradiction dicts with finding_1, finding_2, severity.
        """
        contradictions = []
        negation_words = ["no ", "not ", "never ", "without ", "n't "]
        # Contradiction detection uses lower threshold than deduplication
        contradiction_similarity_threshold = 0.4

        for i, f1 in enumerate(merged):
            for j, f2 in enumerate(merged):
                if i >= j:
                    continue

                text1 = f1["finding"].point.lower()
                text2 = f2["finding"].point.lower()

                # Early termination: length ratio filter
                # If lengths are very different, texts can't be similar enough
                len1, len2 = len(text1), len(text2)
                if len1 > 0 and len2 > 0:
                    if min(len1, len2) / max(len1, len2) < contradiction_similarity_threshold:
                        continue

                # Check for negation patterns (bidirectional)
                # One text has negation word, the other doesn't
                has_negation_diff = False
                for neg in negation_words:
                    t1_has = neg in text1
                    t2_has = neg in text2
                    if t1_has != t2_has:  # XOR: one has it, other doesn't
                        has_negation_diff = True
                        break

                # Skip expensive similarity check if no negation difference
                if not has_negation_diff:
                    continue

                # Only flag if texts are somewhat similar (same topic)
                if self._text_similarity(text1, text2) > contradiction_similarity_threshold:
                    contradictions.append(
                        {
                            "finding_1": f1["finding"].point,
                            "finding_2": f2["finding"].point,
                            "sources_1": f1["sources"],
                            "sources_2": f2["sources"],
                            "severity": "medium",
                        }
                    )

        return contradictions

    def format_summary(
        self,
        aggregated: dict,
        max_findings: int = 10,
    ) -> str:
        """Format aggregation result as human-readable summary.

        Args:
            aggregated: Result from aggregate_findings().
            max_findings: Maximum findings to include in summary.

        Returns:
            Formatted string summary.
        """
        lines = [
            "=== DeepScan Results Summary ===",
            f"Total findings: {aggregated['total_findings']}",
            f"Unique findings: {aggregated['unique_findings']}",
            f"Deduplication: {aggregated['deduplication_ratio']:.1%}",
            "",
        ]

        if aggregated["contradictions"]:
            lines.append(f"⚠️ {len(aggregated['contradictions'])} contradictions detected")
            lines.append("")

        # P3.3-FIX: Add verification-required section (HITL workflow)
        if aggregated.get("verification_required_count", 0) > 0:
            lines.append(f"🔍 {aggregated['verification_required_count']} findings need verification:")
            lines.append("-" * 40)
            for i, f in enumerate(aggregated.get("verification_required_findings", [])[:max_findings], 1):
                confidence = f["confidence"]
                support = f["support_count"]
                # Issue 5 FIX: Use stored point_clean instead of re-stripping
                point = f.get("point_clean", f["finding"].point)
                lines.append(f"{i}. [{confidence}] {point}")
                if support > 1:
                    lines.append(f"   (supported by {support} chunks)")
            lines.append("")

        lines.append("Top Findings:")
        lines.append("-" * 40)

        for i, f in enumerate(aggregated["aggregated_findings"][:max_findings], 1):
            confidence = f["confidence"]
            support = f["support_count"]
            # Issue 5 FIX: Use stored point_clean if available
            point = f.get("point_clean", f["finding"].point)

            lines.append(f"{i}. [{confidence}] {point}")
            if support > 1:
                lines.append(f"   (supported by {support} chunks)")
            lines.append("")

        return "\n".join(lines)


def aggregate_chunk_results(
    chunk_results: list[ChunkResult],
    query: str,
    similarity_threshold: float = 0.7,
) -> dict:
    """Convenience function for aggregating chunk results.

    Args:
        chunk_results: List of ChunkResult objects.
        query: Original query.
        similarity_threshold: Deduplication threshold.

    Returns:
        Aggregation result dict.
    """
    aggregator = ResultAggregator(similarity_threshold=similarity_threshold)
    return aggregator.aggregate_findings(chunk_results, query)


# =============================================================================
# P3-FIX: FINAL Marker Parsing (FR-007)
# =============================================================================

import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class FinalMarkerType(Enum):
    """Types of termination markers."""

    FINAL = "FINAL"  # Direct answer: FINAL(json_content)
    FINAL_VAR = "FINAL_VAR"  # Variable reference: FINAL_VAR(variable_name)
    NEEDS_MORE = "NEEDS_MORE"  # Need more processing: NEEDS_MORE(reason)
    UNABLE = "UNABLE"  # Cannot complete: UNABLE(reason)


@dataclass
class ParsedFinalMarker:
    """Parsed termination marker."""

    marker_type: FinalMarkerType
    content: Any  # JSON for FINAL, str for others
    raw_match: str  # Original matched text


def parse_final_markers(text: str) -> list[ParsedFinalMarker]:
    """Parse FINAL/FINAL_VAR/NEEDS_MORE/UNABLE markers from agent response.

    P3-FIX: Implements FR-007 termination marker handling.

    Markers:
        - FINAL(json_content): Direct answer in JSON format
        - FINAL_VAR(variable_name): Reference to a REPL variable
        - NEEDS_MORE(reason): Agent needs more processing
        - UNABLE(reason): Agent cannot complete the task

    Args:
        text: Raw text from agent response.

    Returns:
        List of ParsedFinalMarker objects found in the text.
    """
    markers = []

    # Pattern for each marker type
    # Uses non-greedy matching for content, handles nested parentheses for JSON
    patterns = [
        (FinalMarkerType.FINAL, r"FINAL\s*\(\s*(\{.*?\}|\[.*?\]|\".*?\"|'.*?'|\d+|true|false|null)\s*\)"),
        (FinalMarkerType.FINAL_VAR, r"FINAL_VAR\s*\(\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\)"),
        (FinalMarkerType.NEEDS_MORE, r"NEEDS_MORE\s*\(\s*[\"'](.+?)[\"']\s*\)"),
        (FinalMarkerType.UNABLE, r"UNABLE\s*\(\s*[\"'](.+?)[\"']\s*\)"),
    ]

    for marker_type, pattern in patterns:
        for match in re.finditer(pattern, text, re.DOTALL | re.IGNORECASE):
            raw_match = match.group(0)
            content_str = match.group(1)

            # Parse content based on marker type
            if marker_type == FinalMarkerType.FINAL:
                try:
                    content = json.loads(content_str)
                except json.JSONDecodeError:
                    # Try as raw string if not valid JSON
                    content = content_str
            elif marker_type == FinalMarkerType.FINAL_VAR:
                content = content_str  # Variable name
            else:
                content = content_str  # Reason string

            markers.append(
                ParsedFinalMarker(
                    marker_type=marker_type,
                    content=content,
                    raw_match=raw_match,
                )
            )

    return markers


def extract_final_answer(
    text: str,
    namespace: dict[str, Any] | None = None,
) -> tuple[str, Any] | None:
    """Extract final answer from agent response using markers.

    Args:
        text: Raw text from agent response.
        namespace: Optional REPL namespace for FINAL_VAR resolution.

    Returns:
        Tuple of (marker_type, answer) or None if no final marker found.
        For FINAL: ("final", json_content)
        For FINAL_VAR: ("final_var", variable_value)
        For NEEDS_MORE: ("needs_more", reason)
        For UNABLE: ("unable", reason)
    """
    markers = parse_final_markers(text)

    if not markers:
        return None

    # Take the first marker (agents should only emit one)
    marker = markers[0]

    if marker.marker_type == FinalMarkerType.FINAL:
        return ("final", marker.content)
    elif marker.marker_type == FinalMarkerType.FINAL_VAR:
        var_name = marker.content
        if namespace and var_name in namespace:
            return ("final_var", namespace[var_name])
        else:
            return ("final_var_error", f"Variable '{var_name}' not found in namespace")
    elif marker.marker_type == FinalMarkerType.NEEDS_MORE:
        return ("needs_more", marker.content)
    elif marker.marker_type == FinalMarkerType.UNABLE:
        return ("unable", marker.content)

    return None


def has_final_marker(text: str) -> bool:
    """Check if text contains any final marker.

    Args:
        text: Text to check.

    Returns:
        True if any FINAL/FINAL_VAR/NEEDS_MORE/UNABLE marker is present.
    """
    return len(parse_final_markers(text)) > 0
