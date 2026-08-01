"""Unit tests for app.core.deep_learning_vision.pixel_diff_analyzer."""

import pytest

from app.core.deep_learning_vision.enums import VisualRiskLevel
from app.core.deep_learning_vision.exceptions import ImageDimensionMismatchError, InvalidImageDataError
from app.core.deep_learning_vision.models import PixelImage
from app.core.deep_learning_vision.pixel_diff_analyzer import PixelDiffAnalyzer


def _image(width: int, height: int, channels: int, fill: int, changed: dict = None) -> PixelImage:
    """Build a single-channel-friendly PixelImage of `fill` everywhere,
    except pixel coordinates present as keys in `changed`, which are
    set to that value (repeated across every channel)."""
    changed = changed or {}
    pixels = []
    for y in range(height):
        for x in range(width):
            value = changed.get((x, y), fill)
            pixels.extend([value] * channels)
    return PixelImage(width=width, height=height, channels=channels, pixels=tuple(pixels))


def test_compare_identical_images_reports_no_diff():
    baseline = _image(4, 4, 1, 10)
    current = _image(4, 4, 1, 10)

    result = PixelDiffAnalyzer().compare(baseline, current)

    assert result.changed_pixel_count == 0
    assert result.diff_ratio == 0.0
    assert result.regions == []
    assert result.risk_level == VisualRiskLevel.LOW


def test_compare_raises_on_dimension_mismatch():
    baseline = _image(4, 4, 1, 10)
    current = _image(5, 4, 1, 10)

    with pytest.raises(ImageDimensionMismatchError):
        PixelDiffAnalyzer().compare(baseline, current)


def test_compare_raises_on_malformed_pixel_buffer():
    baseline = PixelImage(width=4, height=4, channels=1, pixels=(0,) * 15)
    current = _image(4, 4, 1, 10)

    with pytest.raises(InvalidImageDataError):
        PixelDiffAnalyzer().compare(baseline, current)


def test_compare_detects_single_connected_region_with_correct_bounds():
    baseline = _image(4, 4, 1, 0)
    current = _image(
        4, 4, 1, 0, changed={(1, 1): 255, (2, 1): 255, (1, 2): 255, (2, 2): 255}
    )

    result = PixelDiffAnalyzer().compare(baseline, current)

    assert result.changed_pixel_count == 4
    assert len(result.regions) == 1
    region = result.regions[0]
    assert region.changed_pixel_count == 4
    assert region.bounds.x == 1
    assert region.bounds.y == 1
    assert region.bounds.width == 2
    assert region.bounds.height == 2


def test_compare_detects_multiple_disjoint_regions_sorted_by_size():
    baseline = _image(6, 6, 1, 0)
    current = _image(
        6, 6, 1, 0,
        changed={(0, 0): 255, (4, 4): 255, (5, 4): 255, (4, 5): 255, (5, 5): 255},
    )

    result = PixelDiffAnalyzer().compare(baseline, current)

    assert result.changed_pixel_count == 5
    assert len(result.regions) == 2
    assert result.regions[0].changed_pixel_count == 4
    assert result.regions[1].changed_pixel_count == 1


@pytest.mark.parametrize(
    "changed_count,expected_level",
    [
        (1, VisualRiskLevel.LOW),
        (3, VisualRiskLevel.MODERATE),
        (11, VisualRiskLevel.HIGH),
        (26, VisualRiskLevel.CRITICAL),
    ],
)
def test_compare_classifies_risk_level_by_diff_ratio(changed_count, expected_level):
    baseline = _image(10, 10, 1, 0)
    changed = {divmod(i, 10)[::-1]: 255 for i in range(changed_count)}
    current = _image(10, 10, 1, 0, changed=changed)

    result = PixelDiffAnalyzer().compare(baseline, current)

    assert result.risk_level == expected_level


def test_compare_ignores_sub_threshold_noise():
    baseline = _image(4, 4, 1, 100)
    current = _image(4, 4, 1, 100, changed={(0, 0): 105})

    result = PixelDiffAnalyzer().compare(baseline, current)

    assert result.changed_pixel_count == 0
