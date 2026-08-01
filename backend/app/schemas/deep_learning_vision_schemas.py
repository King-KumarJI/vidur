"""
VIDUR Schemas
Submodule: Deep Learning Vision
Purpose: Request/response shapes for the Deep Learning Vision module's
routes. This module is analysis-only and caller-supplied (it never
captures screenshots itself), so - unlike the other pipeline modules,
which only accept a `root_path` - its request schemas mirror the
caller-supplied input dataclasses in
`app.core.deep_learning_vision.models` (PixelImage, LayoutSnapshot,
VisualSnapshot) field-for-field, so a request body can be converted
directly into those dataclasses. Response schemas mirror the pipeline
output dataclasses' `to_dict()` output. Ships behind the
`MAJOR_DEEP_LEARNING_VISUAL_INSPECTION` feature flag (Article 41-44),
disabled by default.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class BoundingBoxInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: int
    y: int
    width: int
    height: int


class PixelImageInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    width: int = Field(..., gt=0)
    height: int = Field(..., gt=0)
    channels: int = Field(..., gt=0)
    pixels: List[int] = Field(..., description="Flat, row-major pixel buffer.")


class LayoutElementInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    element_id: str
    tag: str
    bounds: BoundingBoxInput
    text: Optional[str] = None


class LayoutSnapshotInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    elements: List[LayoutElementInput] = Field(default_factory=list)


class VisualSnapshotInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(..., min_length=1)
    captured_at: Optional[datetime] = None
    image: Optional[PixelImageInput] = None
    layout: Optional[LayoutSnapshotInput] = None


class VisualComparisonRunRequest(BaseModel):
    """Request to compare two caller-supplied VisualSnapshots."""

    model_config = ConfigDict(extra="forbid")

    baseline: VisualSnapshotInput
    current: VisualSnapshotInput
    canvas_width: Optional[int] = Field(default=None, gt=0)
    canvas_height: Optional[int] = Field(default=None, gt=0)


class BoundingBoxResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: int
    y: int
    width: int
    height: int


class PixelDiffRegionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bounds: BoundingBoxResponse
    changed_pixel_count: int


class PixelDiffResultResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_pixel_count: int
    changed_pixel_count: int
    diff_ratio: float
    regions: List[PixelDiffRegionResponse]
    risk_level: str


class LayoutElementChangeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    element_id: str
    change_type: str
    baseline_bounds: Optional[BoundingBoxResponse] = None
    current_bounds: Optional[BoundingBoxResponse] = None
    detail: str


class LayoutDiffResultResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    changes: List[LayoutElementChangeResponse]
    risk_level: str


class LayoutConsistencyIssueResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue_type: str
    element_ids: List[str]
    detail: str
    risk_level: str


class VisualRegressionFindingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str
    risk_level: str
    message: str
    element_id: Optional[str] = None


class VisualComparisonReportResponse(BaseModel):
    """Mirrors `VisualComparisonReport.to_dict()`."""

    model_config = ConfigDict(extra="forbid")

    project_id: str
    baseline_label: str
    current_label: str
    generated_at: str
    pixel_diff: Optional[PixelDiffResultResponse] = None
    layout_diff: Optional[LayoutDiffResultResponse] = None
    consistency_issues: List[LayoutConsistencyIssueResponse]
    findings: List[VisualRegressionFindingResponse]
    verdict: str
    summary: str
