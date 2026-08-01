"""
VIDUR Core - Deep Learning Vision
Submodule: Models
Purpose: Plain, JSON-serializable data structures for the Deep
Learning Vision pipeline. Two families:
  - Caller-supplied input: PixelImage (width/height/channels + a flat
    pixel buffer), LayoutElement/LayoutSnapshot (a pre-extracted
    bounding-box structure), and VisualSnapshot (the "screenshot" unit
    a caller submits for comparison - image data, layout data, or
    both; this module never captures either itself).
  - Pipeline output: PixelDiffResult, LayoutDiffResult,
    LayoutConsistencyIssue, VisualRegressionFinding, and the
    aggregated VisualComparisonReport.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.core.deep_learning_vision.enums import (
    ComparisonVerdict,
    LayoutChangeType,
    LayoutConsistencyIssueType,
    VisualRiskLevel,
)


@dataclass(frozen=True)
class BoundingBox:
    """An axis-aligned pixel-space rectangle, shared by layout
    elements and by the changed-pixel regions a pixel diff reports."""

    x: int
    y: int
    width: int
    height: int

    @property
    def area(self) -> int:
        return max(self.width, 0) * max(self.height, 0)

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    def intersection_area(self, other: "BoundingBox") -> int:
        """Return the area of overlap between this box and `other`, or
        0 if they do not overlap."""
        overlap_width = min(self.right, other.right) - max(self.x, other.x)
        overlap_height = min(self.bottom, other.bottom) - max(self.y, other.y)
        if overlap_width <= 0 or overlap_height <= 0:
            return 0
        return overlap_width * overlap_height

    def to_dict(self) -> Dict[str, Any]:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}


@dataclass(frozen=True)
class PixelImage:
    """Caller-supplied raster image: declared dimensions plus a flat,
    row-major pixel buffer (`pixels[(y * width + x) * channels + c]`).
    No decoding, capture, or file-format handling is performed by
    VIDUR - the caller is responsible for extracting this data from
    whatever screenshot/rendering source it owns."""

    width: int
    height: int
    channels: int
    pixels: Tuple[int, ...]

    @property
    def pixel_count(self) -> int:
        return self.width * self.height

    def pixel_at(self, x: int, y: int) -> Tuple[int, ...]:
        """Return the channel values for the pixel at (x, y). Does not
        bounds-check or length-check the buffer; callers that accept
        untrusted input should validate the image first."""
        base = (y * self.width + x) * self.channels
        return tuple(self.pixels[base : base + self.channels])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "channels": self.channels,
            "pixel_count": self.pixel_count,
        }


@dataclass(frozen=True)
class LayoutElement:
    """A single UI element from a pre-extracted layout structure (for
    example, one DOM node's rendered bounding box)."""

    element_id: str
    tag: str
    bounds: BoundingBox
    text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "element_id": self.element_id,
            "tag": self.tag,
            "bounds": self.bounds.to_dict(),
            "text": self.text,
        }


@dataclass(frozen=True)
class LayoutSnapshot:
    """A full pre-extracted layout structure: every UI element visible
    at capture time, keyed implicitly by `LayoutElement.element_id`."""

    elements: List[LayoutElement] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"elements": [element.to_dict() for element in self.elements]}


@dataclass(frozen=True)
class VisualSnapshot:
    """The caller-supplied unit compared by this module: a labeled
    point-in-time capture of a UI surface, carrying pixel image data,
    pre-extracted layout data, or both. VIDUR does not produce this
    itself - it is assembled and submitted by the caller (e.g. from a
    browser-automation tool the caller already runs)."""

    project_id: str
    label: str
    captured_at: datetime
    image: Optional[PixelImage] = None
    layout: Optional[LayoutSnapshot] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "label": self.label,
            "captured_at": self.captured_at.isoformat(),
            "image": self.image.to_dict() if self.image is not None else None,
            "layout": self.layout.to_dict() if self.layout is not None else None,
        }


@dataclass(frozen=True)
class PixelDiffRegion:
    """One connected cluster of changed pixels found between two
    PixelImages."""

    bounds: BoundingBox
    changed_pixel_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bounds": self.bounds.to_dict(),
            "changed_pixel_count": self.changed_pixel_count,
        }


@dataclass(frozen=True)
class PixelDiffResult:
    """Aggregated result of a pixel-level comparison between a
    baseline and current PixelImage."""

    total_pixel_count: int
    changed_pixel_count: int
    diff_ratio: float
    regions: List[PixelDiffRegion]
    risk_level: VisualRiskLevel

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_pixel_count": self.total_pixel_count,
            "changed_pixel_count": self.changed_pixel_count,
            "diff_ratio": self.diff_ratio,
            "regions": [region.to_dict() for region in self.regions],
            "risk_level": self.risk_level.value,
        }


@dataclass(frozen=True)
class LayoutElementChange:
    """One structural change detected for a single element between a
    baseline and current LayoutSnapshot."""

    element_id: str
    change_type: LayoutChangeType
    baseline_bounds: Optional[BoundingBox] = None
    current_bounds: Optional[BoundingBox] = None
    detail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "element_id": self.element_id,
            "change_type": self.change_type.value,
            "baseline_bounds": self.baseline_bounds.to_dict() if self.baseline_bounds else None,
            "current_bounds": self.current_bounds.to_dict() if self.current_bounds else None,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class LayoutDiffResult:
    """Aggregated result of a structural comparison between a baseline
    and current LayoutSnapshot."""

    changes: List[LayoutElementChange]
    risk_level: VisualRiskLevel

    def changes_of_type(self, change_type: LayoutChangeType) -> List[LayoutElementChange]:
        return [change for change in self.changes if change.change_type is change_type]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "changes": [change.to_dict() for change in self.changes],
            "risk_level": self.risk_level.value,
        }


@dataclass(frozen=True)
class LayoutConsistencyIssue:
    """One intra-snapshot layout consistency problem, detected on a
    single LayoutSnapshot independent of any baseline comparison."""

    issue_type: LayoutConsistencyIssueType
    element_ids: List[str]
    detail: str
    risk_level: VisualRiskLevel

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_type": self.issue_type.value,
            "element_ids": list(self.element_ids),
            "detail": self.detail,
            "risk_level": self.risk_level.value,
        }


@dataclass(frozen=True)
class VisualRegressionFinding:
    """A single, human-readable finding surfaced by the Visual
    Regression Detector, derived from a pixel diff, a layout diff, or
    a layout consistency issue."""

    category: str
    risk_level: VisualRiskLevel
    message: str
    element_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "risk_level": self.risk_level.value,
            "message": self.message,
            "element_id": self.element_id,
        }


@dataclass
class VisualComparisonReport:
    """Aggregated result of a single Deep Learning Vision comparison
    run between a baseline and current VisualSnapshot."""

    project_id: str
    baseline_label: str
    current_label: str
    generated_at: datetime
    pixel_diff: Optional[PixelDiffResult] = None
    layout_diff: Optional[LayoutDiffResult] = None
    consistency_issues: List[LayoutConsistencyIssue] = field(default_factory=list)
    findings: List[VisualRegressionFinding] = field(default_factory=list)
    verdict: ComparisonVerdict = ComparisonVerdict.MATCH
    summary: str = ""

    def findings_by_risk_level(self, minimum_level: VisualRiskLevel) -> List[VisualRegressionFinding]:
        """Return findings at or above `minimum_level`, highest risk
        first."""
        return sorted(
            (f for f in self.findings if f.risk_level.weight >= minimum_level.weight),
            key=lambda f: -f.risk_level.weight,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "baseline_label": self.baseline_label,
            "current_label": self.current_label,
            "generated_at": self.generated_at.isoformat(),
            "pixel_diff": self.pixel_diff.to_dict() if self.pixel_diff else None,
            "layout_diff": self.layout_diff.to_dict() if self.layout_diff else None,
            "consistency_issues": [issue.to_dict() for issue in self.consistency_issues],
            "findings": [finding.to_dict() for finding in self.findings],
            "verdict": self.verdict.value,
            "summary": self.summary,
        }
