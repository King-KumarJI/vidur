"""Unit tests for app.core.deep_learning_vision.image_embedding_comparator.

Two tiers, per CLAUDE.md's "Real AI/ML/DL/NLP Upgrade" Deep Learning
Vision clause and this task's explicit testing requirement:
  - `TestRealClipModel` loads the actual OpenCLIP checkpoint (no
    injected loader) and runs real inference on two real small PNG
    images - an identical pair (expect a match-level result) and a
    meaningfully different pair (expect a regression-level result) -
    proving the primary path works end-to-end, not just that the
    plumbing compiles. Skipped only if open_clip_torch/torch are not
    installed in the environment running the suite.
  - The remaining tests inject a `clip_loader` that returns None (or a
    model stub that raises at inference time) to deterministically
    prove the automatic fallback to classical OpenCV+SSIM+perceptual-
    hash comparison, without needing to uninstall torch/open_clip_torch
    - the same DI-for-tests pattern this codebase already established
    for `SpecsStorage.database_provider` and `local_agent.py`'s
    injectable collectors.

Threshold values asserted below (e.g. similarity > 0.999 for an
identical pair, < 0.7 for a meaningfully different pair) were
calibrated against this module's actual real-model/real-OpenCV output
for these exact synthetic images before being written, not guessed.
"""

import io

import pytest
from PIL import Image, ImageDraw

from app.core.deep_learning_vision.enums import EmbeddingComparisonMethod, VisualRiskLevel
from app.core.deep_learning_vision.exceptions import InvalidImageDataError
from app.core.deep_learning_vision.image_embedding_comparator import (
    ImageEmbeddingComparator,
    _load_clip_model,
)


def _png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _login_screen(width: int = 224, height: int = 224) -> Image.Image:
    """A synthetic "login screen" UI screenshot: header bar, two input
    fields, and a filled submit button."""
    image = Image.new("RGB", (width, height), color=(245, 245, 245))
    draw = ImageDraw.Draw(image)
    draw.rectangle([20, 20, width - 20, 60], fill=(30, 60, 120))
    draw.text((30, 30), "Welcome back", fill=(255, 255, 255))
    draw.rectangle([40, 100, width - 40, 130], outline=(120, 120, 120))
    draw.rectangle([40, 150, width - 40, 180], outline=(120, 120, 120))
    draw.rectangle([40, 200, width - 40, 230], fill=(40, 130, 60))
    draw.text((60, 208), "Sign In", fill=(255, 255, 255))
    return image


def _completely_different_screen(width: int = 224, height: int = 224) -> Image.Image:
    """A synthetic screen sharing no structure, color scheme, or
    content with `_login_screen` - a real visual regression, not a
    minor pixel-noise variant."""
    image = Image.new("RGB", (width, height), color=(20, 20, 30))
    draw = ImageDraw.Draw(image)
    for offset in range(0, width, 12):
        draw.line([(offset, 0), (0, offset)], fill=(220, 40, 40), width=3)
    draw.ellipse([width // 4, height // 4, 3 * width // 4, 3 * height // 4], fill=(240, 200, 20))
    draw.text((width // 2 - 30, height // 2 - 10), "404", fill=(10, 10, 10))
    return image


def _login_screen_with_moved_button(width: int = 224, height: int = 224) -> Image.Image:
    """The same login screen with only the submit button nudged and
    recolored - a minor difference, not a regression."""
    image = Image.new("RGB", (width, height), color=(245, 245, 245))
    draw = ImageDraw.Draw(image)
    draw.rectangle([20, 20, width - 20, 60], fill=(30, 60, 120))
    draw.text((30, 30), "Welcome back", fill=(255, 255, 255))
    draw.rectangle([40, 100, width - 40, 130], outline=(120, 120, 120))
    draw.rectangle([40, 150, width - 40, 180], outline=(120, 120, 120))
    draw.rectangle([44, 204, width - 36, 234], fill=(40, 130, 60))
    draw.text((64, 212), "Sign In", fill=(255, 255, 255))
    return image


_LOGIN_SCREEN_BYTES = _png_bytes(_login_screen())
_DIFFERENT_SCREEN_BYTES = _png_bytes(_completely_different_screen())
_MOVED_BUTTON_SCREEN_BYTES = _png_bytes(_login_screen_with_moved_button())


def _clip_available() -> bool:
    return _load_clip_model() is not None


@pytest.mark.skipif(
    not _clip_available(), reason="open_clip_torch/torch not installed/loadable in this environment"
)
class TestRealClipModel:
    """Exercises the real, installed OpenCLIP checkpoint - no injected
    loader anywhere in this class."""

    def test_identical_images_are_reported_as_a_match(self):
        comparator = ImageEmbeddingComparator()

        result = comparator.compare(_LOGIN_SCREEN_BYTES, _LOGIN_SCREEN_BYTES)

        assert result.method == EmbeddingComparisonMethod.CLIP
        assert result.similarity > 0.999
        assert result.risk_level == VisualRiskLevel.LOW

    def test_meaningfully_different_images_are_reported_as_a_regression(self):
        comparator = ImageEmbeddingComparator()

        result = comparator.compare(_LOGIN_SCREEN_BYTES, _DIFFERENT_SCREEN_BYTES)

        assert result.method == EmbeddingComparisonMethod.CLIP
        assert result.similarity < 0.7
        assert result.risk_level == VisualRiskLevel.CRITICAL

    def test_minor_difference_is_not_reported_as_a_regression(self):
        comparator = ImageEmbeddingComparator()

        result = comparator.compare(_LOGIN_SCREEN_BYTES, _MOVED_BUTTON_SCREEN_BYTES)

        assert result.method == EmbeddingComparisonMethod.CLIP
        assert result.risk_level.weight < VisualRiskLevel.HIGH.weight


class TestClassicalFallback:
    """Forces the CLIP path unavailable via an injected `clip_loader`
    returning None, proving the automatic fallback to OpenCV SSIM +
    perceptual hashing actually runs and produces sane results - not
    just that the code path is reachable."""

    @staticmethod
    def _unavailable_comparator() -> ImageEmbeddingComparator:
        return ImageEmbeddingComparator(clip_loader=lambda: None)

    def test_identical_images_via_fallback_score_near_perfect_similarity(self):
        comparator = self._unavailable_comparator()

        result = comparator.compare(_LOGIN_SCREEN_BYTES, _LOGIN_SCREEN_BYTES)

        assert result.method == EmbeddingComparisonMethod.CLASSICAL_FALLBACK
        assert result.ssim_score > 0.999
        assert result.phash_hamming_distance == 0
        assert result.risk_level == VisualRiskLevel.LOW

    def test_meaningfully_different_images_via_fallback_score_low_similarity(self):
        comparator = self._unavailable_comparator()

        result = comparator.compare(_LOGIN_SCREEN_BYTES, _DIFFERENT_SCREEN_BYTES)

        assert result.method == EmbeddingComparisonMethod.CLASSICAL_FALLBACK
        assert result.ssim_score < 0.3
        assert result.phash_hamming_distance > 20
        assert result.risk_level == VisualRiskLevel.CRITICAL

    def test_minor_difference_via_fallback_is_not_reported_as_a_regression(self):
        comparator = self._unavailable_comparator()

        result = comparator.compare(_LOGIN_SCREEN_BYTES, _MOVED_BUTTON_SCREEN_BYTES)

        assert result.method == EmbeddingComparisonMethod.CLASSICAL_FALLBACK
        assert result.risk_level.weight < VisualRiskLevel.CRITICAL.weight

    def test_falls_back_when_a_loaded_clip_model_raises_at_inference_time(self):
        class _BrokenClipModel:
            torch = None
            preprocess = None
            model = None

        comparator = ImageEmbeddingComparator(clip_loader=lambda: _BrokenClipModel())

        result = comparator.compare(_LOGIN_SCREEN_BYTES, _LOGIN_SCREEN_BYTES)

        assert result.method == EmbeddingComparisonMethod.CLASSICAL_FALLBACK

    def test_decode_invalid_bytes_raises_invalid_image_data_error(self):
        comparator = self._unavailable_comparator()

        with pytest.raises(InvalidImageDataError):
            comparator.compare(b"not-an-image", b"also-not-an-image")

    def test_fallback_handles_differently_sized_images(self):
        small = _png_bytes(_login_screen(width=100, height=100))
        large = _png_bytes(_login_screen(width=300, height=250))
        comparator = self._unavailable_comparator()

        result = comparator.compare(small, large)

        assert result.method == EmbeddingComparisonMethod.CLASSICAL_FALLBACK
        assert 0.0 <= result.ssim_score <= 1.0
