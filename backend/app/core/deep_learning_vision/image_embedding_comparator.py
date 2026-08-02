"""
VIDUR Core - Deep Learning Vision
Submodule: Image Embedding Comparator
Purpose: Real-screenshot comparison, per CLAUDE.md's "Real AI/ML/DL/NLP
Upgrade" Deep Learning Vision clause. Primary path: OpenCLIP
(open_clip_torch + torch), inference only, no training - extracts a
feature embedding for each caller-supplied screenshot image and
compares them via cosine similarity to detect visual inconsistencies,
layout changes, missing components, alignment issues, and regressions.
Automatic fallback, whenever OpenCLIP/torch cannot be imported or the
model fails to load, to classical computer vision: OpenCV +
Structural Similarity Index (SSIM, hand-implemented via OpenCV's
Gaussian blur - no scikit-image dependency needed) + perceptual
hashing (imagehash). Fully offline at inference time: the CLIP
checkpoint is downloaded once by open_clip/torch and cached locally on
disk (the same one-time-download pattern the NLP module's spaCy
`en_core_web_sm` pipeline already established), never a per-call
network request, API key, or cloud inference call.
"""

import io
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Callable, Optional

import numpy as np

from app.config.logging_config import get_logger
from app.core.deep_learning_vision.enums import EmbeddingComparisonMethod, VisualRiskLevel
from app.core.deep_learning_vision.exceptions import InvalidImageDataError
from app.core.deep_learning_vision.models import ImageEmbeddingComparisonResult

logger = get_logger("deep_learning_vision.image_embedding_comparator")

#: OpenCLIP model architecture + pretrained-weights tag. ViT-B-32 is
#: OpenCLIP's standard baseline checkpoint (~350MB, downloaded once and
#: cached by open_clip/torch) - small enough to run comfortably on CPU
#: while still producing a well-separated embedding space for detecting
#: real visual regressions.
CLIP_MODEL_NAME = "ViT-B-32"
CLIP_PRETRAINED_TAG = "openai"

#: CLIP cosine-similarity thresholds. Identical images embed to
#: similarity ~1.0; unrelated UI screenshots typically fall well below
#: 0.85 even though CLIP's embedding space is generally "tight" (all
#: images share some similarity) since it was trained on natural
#: image/caption pairs, not UI screenshots specifically.
CLIP_LOW_RISK_THRESHOLD = 0.98
CLIP_MODERATE_RISK_THRESHOLD = 0.92
CLIP_HIGH_RISK_THRESHOLD = 0.80

#: Classical-fallback thresholds, combining windowed SSIM (1.0 =
#: identical) with perceptual-hash Hamming distance (0 = identical, up
#: to 64 for a 64-bit phash) as a secondary corroborating signal.
SSIM_LOW_RISK_THRESHOLD = 0.98
SSIM_MODERATE_RISK_THRESHOLD = 0.90
SSIM_HIGH_RISK_THRESHOLD = 0.70
PHASH_LOW_RISK_MAX_DISTANCE = 2
PHASH_MODERATE_RISK_MAX_DISTANCE = 8
PHASH_HIGH_RISK_MAX_DISTANCE = 20

#: SSIM's standard stabilizing constants (Wang et al. 2004), scaled for
#: an 8-bit (0-255) pixel value range.
_SSIM_C1 = (0.01 * 255) ** 2
_SSIM_C2 = (0.03 * 255) ** 2
_SSIM_GAUSSIAN_KERNEL_SIZE = (11, 11)
_SSIM_GAUSSIAN_SIGMA = 1.5


@dataclass
class _ClipModel:
    """Loaded OpenCLIP model plus its matching preprocessing transform
    and the `torch` module itself (imported lazily, so a caller-injected
    loader can construct this without importing torch at module load
    time)."""

    model: Any
    preprocess: Any
    torch: Any


@lru_cache(maxsize=1)
def _load_clip_model() -> Optional[_ClipModel]:
    """Load and cache the OpenCLIP model for the lifetime of this
    process. Returns None (never raises) if `open_clip_torch`/`torch`
    are not installed, or if loading the pretrained checkpoint fails
    for any reason (no cached weights and no network access, corrupt
    cache, unsupported platform, etc.) - the caller falls back to
    classical CV comparison in either case, matching the NLP module's
    `_load_spacy_model` fallback pattern."""
    try:
        import torch
        import open_clip
    except ImportError as exc:
        logger.warning(
            "open_clip_torch/torch not installed; falling back to classical "
            "OpenCV+SSIM+perceptual-hash comparison. To enable the primary "
            "CLIP path, run: pip install torch open_clip_torch (%s)",
            exc,
        )
        return None

    try:
        model, _, preprocess = open_clip.create_model_and_transforms(
            CLIP_MODEL_NAME, pretrained=CLIP_PRETRAINED_TAG
        )
        model.eval()
        return _ClipModel(model=model, preprocess=preprocess, torch=torch)
    except Exception as exc:  # model/checkpoint load can fail many ways; never crash a comparison run
        logger.warning(
            "Failed to load OpenCLIP model '%s' (pretrained=%s): %s; "
            "falling back to classical OpenCV+SSIM+perceptual-hash comparison.",
            CLIP_MODEL_NAME,
            CLIP_PRETRAINED_TAG,
            exc,
        )
        return None


def _classify_clip(similarity: float) -> VisualRiskLevel:
    if similarity >= CLIP_LOW_RISK_THRESHOLD:
        return VisualRiskLevel.LOW
    if similarity >= CLIP_MODERATE_RISK_THRESHOLD:
        return VisualRiskLevel.MODERATE
    if similarity >= CLIP_HIGH_RISK_THRESHOLD:
        return VisualRiskLevel.HIGH
    return VisualRiskLevel.CRITICAL


def _classify_classical(ssim_score: float, phash_distance: int) -> VisualRiskLevel:
    if ssim_score >= SSIM_LOW_RISK_THRESHOLD and phash_distance <= PHASH_LOW_RISK_MAX_DISTANCE:
        return VisualRiskLevel.LOW
    if ssim_score >= SSIM_MODERATE_RISK_THRESHOLD and phash_distance <= PHASH_MODERATE_RISK_MAX_DISTANCE:
        return VisualRiskLevel.MODERATE
    if ssim_score >= SSIM_HIGH_RISK_THRESHOLD and phash_distance <= PHASH_HIGH_RISK_MAX_DISTANCE:
        return VisualRiskLevel.HIGH
    return VisualRiskLevel.CRITICAL


class ImageEmbeddingComparator:
    """Compares two real screenshot images (raw file bytes - PNG, JPEG,
    etc.) via OpenCLIP feature-embedding cosine similarity, falling back
    automatically to classical computer vision (OpenCV windowed SSIM +
    perceptual hashing) whenever the CLIP path is unavailable."""

    def __init__(self, clip_loader: Callable[[], Optional[_ClipModel]] = _load_clip_model) -> None:
        #: Injectable so tests can force the fallback path deterministically
        #: (return None) without uninstalling torch/open_clip_torch, the
        #: same DI-for-tests pattern `SpecsStorage.database_provider` and
        #: `local_agent.py`'s injectable collectors already establish.
        self._clip_loader = clip_loader

    def compare(self, baseline_bytes: bytes, current_bytes: bytes) -> ImageEmbeddingComparisonResult:
        """Compare two real screenshot images supplied as raw file
        bytes.

        Raises InvalidImageDataError if either byte string cannot be
        decoded as an image.
        """
        baseline_image = self._decode(baseline_bytes)
        current_image = self._decode(current_bytes)

        clip_model = self._clip_loader()
        if clip_model is not None:
            try:
                return self._compare_with_clip(clip_model, baseline_image, current_image)
            except Exception as exc:  # a loaded model can still fail at inference time
                logger.warning(
                    "OpenCLIP inference failed (%s); falling back to classical "
                    "OpenCV+SSIM+perceptual-hash comparison for this run.",
                    exc,
                )

        return self._compare_with_classical_cv(baseline_image, current_image)

    @staticmethod
    def _decode(image_bytes: bytes) -> "Any":
        try:
            from PIL import Image
        except ImportError as exc:
            raise InvalidImageDataError(
                "Pillow is required to decode real screenshot image bytes but is not installed."
            ) from exc
        try:
            return Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except Exception as exc:
            raise InvalidImageDataError(f"Could not decode image bytes as an image: {exc}") from exc

    @staticmethod
    def _compare_with_clip(
        clip_model: _ClipModel, baseline_image: Any, current_image: Any
    ) -> ImageEmbeddingComparisonResult:
        torch = clip_model.torch
        with torch.no_grad():
            baseline_tensor = clip_model.preprocess(baseline_image).unsqueeze(0)
            current_tensor = clip_model.preprocess(current_image).unsqueeze(0)
            baseline_features = clip_model.model.encode_image(baseline_tensor)
            current_features = clip_model.model.encode_image(current_tensor)
            baseline_features = baseline_features / baseline_features.norm(dim=-1, keepdim=True)
            current_features = current_features / current_features.norm(dim=-1, keepdim=True)
            similarity = float((baseline_features @ current_features.T).item())

        similarity = max(-1.0, min(1.0, similarity))
        risk_level = _classify_clip(similarity)
        return ImageEmbeddingComparisonResult(
            method=EmbeddingComparisonMethod.CLIP,
            similarity=round(similarity, 4),
            risk_level=risk_level,
            detail=(
                f"OpenCLIP ({CLIP_MODEL_NAME}/{CLIP_PRETRAINED_TAG}) cosine similarity: "
                f"{similarity:.4f}."
            ),
        )

    @staticmethod
    def _compare_with_classical_cv(baseline_image: Any, current_image: Any) -> ImageEmbeddingComparisonResult:
        try:
            import cv2
        except ImportError as exc:
            raise InvalidImageDataError(
                "opencv-python-headless is required for the classical CV fallback comparison "
                "but is not installed."
            ) from exc
        try:
            import imagehash
        except ImportError as exc:
            raise InvalidImageDataError(
                "imagehash is required for the classical CV fallback comparison but is not installed."
            ) from exc

        ssim_score = _compute_ssim(cv2, baseline_image, current_image)
        baseline_hash = imagehash.phash(baseline_image)
        current_hash = imagehash.phash(current_image)
        phash_distance = int(baseline_hash - current_hash)

        risk_level = _classify_classical(ssim_score, phash_distance)
        return ImageEmbeddingComparisonResult(
            method=EmbeddingComparisonMethod.CLASSICAL_FALLBACK,
            similarity=round(max(0.0, min(1.0, ssim_score)), 4),
            risk_level=risk_level,
            detail=(
                f"Classical CV fallback (OpenCV SSIM={ssim_score:.4f}, "
                f"perceptual-hash Hamming distance={phash_distance})."
            ),
            ssim_score=round(ssim_score, 4),
            phash_hamming_distance=phash_distance,
        )


def _compute_ssim(cv2: Any, baseline_image: Any, current_image: Any) -> float:
    """Windowed Structural Similarity Index (Wang et al. 2004) between
    two PIL images, computed directly with OpenCV primitives (Gaussian
    blur for local means/variances/covariance) rather than a
    scikit-image dependency, since only opencv-python-headless and
    imagehash were approved for this fallback path. Images are
    converted to grayscale and resized to a common size (the current
    image's dimensions) before comparison, since SSIM requires
    pixel-aligned inputs."""
    baseline_array = np.array(baseline_image.convert("L"), dtype=np.float64)
    current_array = np.array(current_image.convert("L"), dtype=np.float64)

    if baseline_array.shape != current_array.shape:
        target_size = (current_array.shape[1], current_array.shape[0])
        baseline_array = cv2.resize(baseline_array, target_size, interpolation=cv2.INTER_AREA).astype(
            np.float64
        )

    kernel_size = _SSIM_GAUSSIAN_KERNEL_SIZE
    sigma = _SSIM_GAUSSIAN_SIGMA

    mu_baseline = cv2.GaussianBlur(baseline_array, kernel_size, sigma)
    mu_current = cv2.GaussianBlur(current_array, kernel_size, sigma)

    mu_baseline_sq = mu_baseline**2
    mu_current_sq = mu_current**2
    mu_baseline_current = mu_baseline * mu_current

    sigma_baseline_sq = cv2.GaussianBlur(baseline_array**2, kernel_size, sigma) - mu_baseline_sq
    sigma_current_sq = cv2.GaussianBlur(current_array**2, kernel_size, sigma) - mu_current_sq
    sigma_baseline_current = (
        cv2.GaussianBlur(baseline_array * current_array, kernel_size, sigma) - mu_baseline_current
    )

    numerator = (2 * mu_baseline_current + _SSIM_C1) * (2 * sigma_baseline_current + _SSIM_C2)
    denominator = (mu_baseline_sq + mu_current_sq + _SSIM_C1) * (
        sigma_baseline_sq + sigma_current_sq + _SSIM_C2
    )
    ssim_map = numerator / denominator
    return float(np.mean(ssim_map))
