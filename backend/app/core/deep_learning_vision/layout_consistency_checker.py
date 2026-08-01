"""
VIDUR Core - Deep Learning Vision
Submodule: Layout Consistency Checker
Purpose: Intra-snapshot layout consistency checks (per Chapter VII
"layout consistency"), independent of any baseline comparison: element
overlap, off-canvas placement, zero-size elements, and duplicate
element identifiers within a single caller-supplied LayoutSnapshot.
"""

from collections import defaultdict
from itertools import combinations
from typing import Dict, List, Optional

from app.core.deep_learning_vision.enums import LayoutConsistencyIssueType, VisualRiskLevel
from app.core.deep_learning_vision.models import LayoutConsistencyIssue, LayoutElement, LayoutSnapshot

#: An overlap covering at least this fraction of the smaller element's
#: area is reported as an OVERLAPPING_ELEMENTS issue. Small incidental
#: overlaps (e.g. a border or shadow) below this are not flagged.
OVERLAP_RATIO_THRESHOLD = 0.3

#: An overlap at or above this fraction is escalated from MODERATE to
#: HIGH severity - most of one element is obscured by another.
OVERLAP_RATIO_HIGH_THRESHOLD = 0.7


class LayoutConsistencyChecker:
    """Detects structural consistency problems within one
    LayoutSnapshot."""

    def check(
        self,
        layout: LayoutSnapshot,
        canvas_width: Optional[int] = None,
        canvas_height: Optional[int] = None,
    ) -> List[LayoutConsistencyIssue]:
        """Return every consistency issue found in `layout`. If
        `canvas_width`/`canvas_height` are supplied, elements extending
        beyond them (or with negative position) are flagged as
        off-canvas; without them, only negative-position elements are
        flagged."""
        issues: List[LayoutConsistencyIssue] = []
        issues.extend(self._duplicate_ids(layout.elements))
        issues.extend(self._zero_size_elements(layout.elements))
        issues.extend(self._off_canvas_elements(layout.elements, canvas_width, canvas_height))
        issues.extend(self._overlapping_elements(layout.elements))
        return issues

    @staticmethod
    def _duplicate_ids(elements: List[LayoutElement]) -> List[LayoutConsistencyIssue]:
        seen: Dict[str, int] = defaultdict(int)
        for element in elements:
            seen[element.element_id] += 1

        return [
            LayoutConsistencyIssue(
                issue_type=LayoutConsistencyIssueType.DUPLICATE_ELEMENT_ID,
                element_ids=[element_id],
                detail=f"Element id '{element_id}' appears {count} times in the same layout snapshot.",
                risk_level=VisualRiskLevel.HIGH,
            )
            for element_id, count in seen.items()
            if count > 1
        ]

    @staticmethod
    def _zero_size_elements(elements: List[LayoutElement]) -> List[LayoutConsistencyIssue]:
        return [
            LayoutConsistencyIssue(
                issue_type=LayoutConsistencyIssueType.ZERO_SIZE_ELEMENT,
                element_ids=[element.element_id],
                detail=(
                    f"Element '{element.element_id}' has non-positive size "
                    f"({element.bounds.width}x{element.bounds.height})."
                ),
                risk_level=VisualRiskLevel.HIGH,
            )
            for element in elements
            if element.bounds.width <= 0 or element.bounds.height <= 0
        ]

    @staticmethod
    def _off_canvas_elements(
        elements: List[LayoutElement],
        canvas_width: Optional[int],
        canvas_height: Optional[int],
    ) -> List[LayoutConsistencyIssue]:
        issues: List[LayoutConsistencyIssue] = []
        for element in elements:
            bounds = element.bounds
            out_of_bounds = bounds.x < 0 or bounds.y < 0
            if canvas_width is not None and bounds.right > canvas_width:
                out_of_bounds = True
            if canvas_height is not None and bounds.bottom > canvas_height:
                out_of_bounds = True

            if out_of_bounds:
                issues.append(
                    LayoutConsistencyIssue(
                        issue_type=LayoutConsistencyIssueType.OFF_CANVAS_ELEMENT,
                        element_ids=[element.element_id],
                        detail=(
                            f"Element '{element.element_id}' bounds "
                            f"(x={bounds.x}, y={bounds.y}, right={bounds.right}, bottom={bounds.bottom}) "
                            f"fall outside the canvas."
                        ),
                        risk_level=VisualRiskLevel.MODERATE,
                    )
                )
        return issues

    @staticmethod
    def _overlapping_elements(elements: List[LayoutElement]) -> List[LayoutConsistencyIssue]:
        issues: List[LayoutConsistencyIssue] = []
        for first, second in combinations(elements, 2):
            overlap_area = first.bounds.intersection_area(second.bounds)
            if overlap_area <= 0:
                continue

            smaller_area = min(first.bounds.area, second.bounds.area)
            if smaller_area <= 0:
                continue

            overlap_ratio = overlap_area / smaller_area
            if overlap_ratio < OVERLAP_RATIO_THRESHOLD:
                continue

            risk_level = (
                VisualRiskLevel.HIGH
                if overlap_ratio >= OVERLAP_RATIO_HIGH_THRESHOLD
                else VisualRiskLevel.MODERATE
            )
            issues.append(
                LayoutConsistencyIssue(
                    issue_type=LayoutConsistencyIssueType.OVERLAPPING_ELEMENTS,
                    element_ids=[first.element_id, second.element_id],
                    detail=(
                        f"Elements '{first.element_id}' and '{second.element_id}' overlap by "
                        f"{overlap_ratio:.0%} of the smaller element's area."
                    ),
                    risk_level=risk_level,
                )
            )
        return issues
