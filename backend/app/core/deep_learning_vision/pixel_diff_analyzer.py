"""
VIDUR Core - Deep Learning Vision
Submodule: Pixel Diff Analyzer
Purpose: Stdlib-only pixel-level comparison between two caller-
supplied PixelImages (per Chapter VII "screenshot analysis" / "UI
comparison"). Flags per-pixel changes above a noise threshold,
clusters them into connected-component bounding-box regions, and
classifies the overall diff by the fraction of the image that
changed. No Pillow/numpy dependency: pure Python over the caller's
flat pixel buffer.
"""

from collections import deque
from typing import Deque, List, Set, Tuple

from app.core.deep_learning_vision.enums import VisualRiskLevel
from app.core.deep_learning_vision.exceptions import ImageDimensionMismatchError, InvalidImageDataError
from app.core.deep_learning_vision.models import BoundingBox, PixelDiffRegion, PixelDiffResult, PixelImage

#: Minimum summed absolute per-channel difference for a pixel to be
#: considered "changed". Below this, ordinary anti-aliasing/compression
#: noise is not treated as a visual difference.
PIXEL_CHANGE_THRESHOLD = 24

#: Maximum number of connected-component regions reported. Real
#: regressions cluster into a handful of large regions; beyond this
#: count, additional small/scattered regions add noise rather than
#: signal, so only the largest are kept.
MAX_REPORTED_REGIONS = 25

CRITICAL_DIFF_RATIO_THRESHOLD = 0.25
HIGH_DIFF_RATIO_THRESHOLD = 0.10
MODERATE_DIFF_RATIO_THRESHOLD = 0.02

_NEIGHBOR_OFFSETS: Tuple[Tuple[int, int], ...] = ((1, 0), (-1, 0), (0, 1), (0, -1))


def _classify(diff_ratio: float) -> VisualRiskLevel:
    if diff_ratio >= CRITICAL_DIFF_RATIO_THRESHOLD:
        return VisualRiskLevel.CRITICAL
    if diff_ratio >= HIGH_DIFF_RATIO_THRESHOLD:
        return VisualRiskLevel.HIGH
    if diff_ratio >= MODERATE_DIFF_RATIO_THRESHOLD:
        return VisualRiskLevel.MODERATE
    return VisualRiskLevel.LOW


class PixelDiffAnalyzer:
    """Compares two same-sized PixelImages pixel-for-pixel."""

    def compare(self, baseline: PixelImage, current: PixelImage) -> PixelDiffResult:
        """Return a PixelDiffResult describing every changed pixel and
        the connected regions they form.

        Raises InvalidImageDataError if either image's pixel buffer
        length does not match its declared width/height/channels, and
        ImageDimensionMismatchError if the two images do not share the
        same width, height, and channel count.
        """
        self._validate(baseline)
        self._validate(current)
        if (
            baseline.width != current.width
            or baseline.height != current.height
            or baseline.channels != current.channels
        ):
            raise ImageDimensionMismatchError(
                f"Cannot compare images of differing dimensions: "
                f"baseline is {baseline.width}x{baseline.height}x{baseline.channels}, "
                f"current is {current.width}x{current.height}x{current.channels}."
            )

        total_pixel_count = current.width * current.height
        changed = self._changed_pixels(baseline, current)
        regions = self._cluster_regions(changed)

        diff_ratio = round(len(changed) / total_pixel_count, 4) if total_pixel_count else 0.0

        return PixelDiffResult(
            total_pixel_count=total_pixel_count,
            changed_pixel_count=len(changed),
            diff_ratio=diff_ratio,
            regions=regions,
            risk_level=_classify(diff_ratio),
        )

    @staticmethod
    def _validate(image: PixelImage) -> None:
        if image.width <= 0 or image.height <= 0 or image.channels <= 0:
            raise InvalidImageDataError(
                f"PixelImage dimensions must be positive, got "
                f"{image.width}x{image.height}x{image.channels}."
            )
        expected_length = image.width * image.height * image.channels
        if len(image.pixels) != expected_length:
            raise InvalidImageDataError(
                f"PixelImage pixel buffer length {len(image.pixels)} does not match "
                f"width*height*channels ({expected_length})."
            )

    @staticmethod
    def _changed_pixels(baseline: PixelImage, current: PixelImage) -> Set[Tuple[int, int]]:
        width, height, channels = current.width, current.height, current.channels
        changed: Set[Tuple[int, int]] = set()
        for y in range(height):
            row_base = y * width * channels
            for x in range(width):
                base = row_base + x * channels
                diff = sum(
                    abs(baseline.pixels[base + c] - current.pixels[base + c]) for c in range(channels)
                )
                if diff >= PIXEL_CHANGE_THRESHOLD:
                    changed.add((x, y))
        return changed

    @staticmethod
    def _cluster_regions(changed: Set[Tuple[int, int]]) -> List[PixelDiffRegion]:
        """Group changed pixel coordinates into 4-connected components
        via breadth-first search, then reduce each component to its
        bounding box."""
        remaining = set(changed)
        regions: List[PixelDiffRegion] = []

        while remaining:
            start = next(iter(remaining))
            queue: Deque[Tuple[int, int]] = deque([start])
            remaining.discard(start)
            component: List[Tuple[int, int]] = []

            while queue:
                x, y = queue.popleft()
                component.append((x, y))
                for dx, dy in _NEIGHBOR_OFFSETS:
                    neighbor = (x + dx, y + dy)
                    if neighbor in remaining:
                        remaining.discard(neighbor)
                        queue.append(neighbor)

            min_x = min(px for px, _ in component)
            max_x = max(px for px, _ in component)
            min_y = min(py for _, py in component)
            max_y = max(py for _, py in component)
            regions.append(
                PixelDiffRegion(
                    bounds=BoundingBox(x=min_x, y=min_y, width=max_x - min_x + 1, height=max_y - min_y + 1),
                    changed_pixel_count=len(component),
                )
            )

        regions.sort(key=lambda region: -region.changed_pixel_count)
        return regions[:MAX_REPORTED_REGIONS]
