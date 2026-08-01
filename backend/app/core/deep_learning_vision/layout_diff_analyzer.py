"""
VIDUR Core - Deep Learning Vision
Submodule: Layout Diff Analyzer
Purpose: Structural comparison between two caller-supplied
LayoutSnapshots (per Chapter VII "UI comparison" / "visual regression
detection"), matching elements by `element_id` and classifying each as
added, removed, moved, resized, or modified (text/tag change).
"""

from typing import Dict, List

from app.core.deep_learning_vision.enums import LayoutChangeType, VisualRiskLevel
from app.core.deep_learning_vision.models import LayoutElement, LayoutElementChange, LayoutDiffResult, LayoutSnapshot

#: An element whose position shifts by at least this many pixels on
#: either axis is considered "moved" rather than unchanged jitter.
MOVE_TOLERANCE_PX = 2

#: An element whose width or height changes by at least this many
#: pixels is considered "resized".
RESIZE_TOLERANCE_PX = 2

#: Relative severity of each change type when computing the overall
#: diff ratio. A removed element is weighted highest: losing a UI
#: element outright is a more severe regression than one that merely
#: moved, resized, or had its text changed.
_CHANGE_TYPE_WEIGHT = {
    LayoutChangeType.ADDED: 1.0,
    LayoutChangeType.MOVED: 1.0,
    LayoutChangeType.RESIZED: 1.0,
    LayoutChangeType.MODIFIED: 1.0,
    LayoutChangeType.REMOVED: 2.0,
}

CRITICAL_CHANGE_RATIO_THRESHOLD = 0.5
HIGH_CHANGE_RATIO_THRESHOLD = 0.25
MODERATE_CHANGE_RATIO_THRESHOLD = 0.1


def _classify(change_ratio: float) -> VisualRiskLevel:
    if change_ratio >= CRITICAL_CHANGE_RATIO_THRESHOLD:
        return VisualRiskLevel.CRITICAL
    if change_ratio >= HIGH_CHANGE_RATIO_THRESHOLD:
        return VisualRiskLevel.HIGH
    if change_ratio >= MODERATE_CHANGE_RATIO_THRESHOLD:
        return VisualRiskLevel.MODERATE
    return VisualRiskLevel.LOW


class LayoutDiffAnalyzer:
    """Compares two LayoutSnapshots element-by-element."""

    def compare(self, baseline: LayoutSnapshot, current: LayoutSnapshot) -> LayoutDiffResult:
        baseline_by_id: Dict[str, LayoutElement] = {e.element_id: e for e in baseline.elements}
        current_by_id: Dict[str, LayoutElement] = {e.element_id: e for e in current.elements}

        changes: List[LayoutElementChange] = []

        for element_id, element in current_by_id.items():
            if element_id not in baseline_by_id:
                changes.append(
                    LayoutElementChange(
                        element_id=element_id,
                        change_type=LayoutChangeType.ADDED,
                        current_bounds=element.bounds,
                        detail=f"Element '{element_id}' is present in the current layout but not the baseline.",
                    )
                )

        for element_id, element in baseline_by_id.items():
            if element_id not in current_by_id:
                changes.append(
                    LayoutElementChange(
                        element_id=element_id,
                        change_type=LayoutChangeType.REMOVED,
                        baseline_bounds=element.bounds,
                        detail=f"Element '{element_id}' is present in the baseline but not the current layout.",
                    )
                )

        for element_id in set(baseline_by_id) & set(current_by_id):
            changes.extend(
                self._compare_matched_element(baseline_by_id[element_id], current_by_id[element_id])
            )

        total_elements = len(set(baseline_by_id) | set(current_by_id)) or 1
        weighted_change_score = sum(_CHANGE_TYPE_WEIGHT[change.change_type] for change in changes)
        change_ratio = round(weighted_change_score / total_elements, 4)

        return LayoutDiffResult(changes=changes, risk_level=_classify(change_ratio))

    @staticmethod
    def _compare_matched_element(
        baseline_element: LayoutElement, current_element: LayoutElement
    ) -> List[LayoutElementChange]:
        changes: List[LayoutElementChange] = []
        element_id = current_element.element_id
        baseline_bounds = baseline_element.bounds
        current_bounds = current_element.bounds

        dx = abs(current_bounds.x - baseline_bounds.x)
        dy = abs(current_bounds.y - baseline_bounds.y)
        if dx >= MOVE_TOLERANCE_PX or dy >= MOVE_TOLERANCE_PX:
            changes.append(
                LayoutElementChange(
                    element_id=element_id,
                    change_type=LayoutChangeType.MOVED,
                    baseline_bounds=baseline_bounds,
                    current_bounds=current_bounds,
                    detail=f"Element '{element_id}' moved by ({dx}px, {dy}px).",
                )
            )

        dwidth = abs(current_bounds.width - baseline_bounds.width)
        dheight = abs(current_bounds.height - baseline_bounds.height)
        if dwidth >= RESIZE_TOLERANCE_PX or dheight >= RESIZE_TOLERANCE_PX:
            changes.append(
                LayoutElementChange(
                    element_id=element_id,
                    change_type=LayoutChangeType.RESIZED,
                    baseline_bounds=baseline_bounds,
                    current_bounds=current_bounds,
                    detail=(
                        f"Element '{element_id}' resized from "
                        f"{baseline_bounds.width}x{baseline_bounds.height} to "
                        f"{current_bounds.width}x{current_bounds.height}."
                    ),
                )
            )

        if (
            baseline_element.text != current_element.text
            or baseline_element.tag != current_element.tag
        ):
            changes.append(
                LayoutElementChange(
                    element_id=element_id,
                    change_type=LayoutChangeType.MODIFIED,
                    baseline_bounds=baseline_bounds,
                    current_bounds=current_bounds,
                    detail=f"Element '{element_id}' tag/text content changed.",
                )
            )

        return changes
