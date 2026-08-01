"""
VIDUR Core - Deep Learning Vision
Submodule: Exceptions
Purpose: Exception types for the Deep Learning Vision pipeline
(pixel-level image comparison, layout structural diffing, layout
consistency checking, and visual regression detection over
caller-supplied screenshot data).
"""


class DeepLearningVisionError(Exception):
    """Base class for all Deep Learning Vision errors."""


class DeepLearningVisionDisabledError(DeepLearningVisionError):
    """Raised when a visual comparison run is requested while the
    MAJOR_DEEP_LEARNING_VISUAL_INSPECTION feature flag is disabled."""


class InvalidImageDataError(DeepLearningVisionError):
    """Raised when a supplied PixelImage's pixel buffer does not match
    its declared width, height, and channel count, or otherwise fails
    structural validation."""


class InvalidLayoutDataError(DeepLearningVisionError):
    """Raised when a supplied LayoutSnapshot or LayoutElement fails
    structural validation."""


class ImageDimensionMismatchError(DeepLearningVisionError):
    """Raised when two PixelImages being compared do not share the same
    width, height, and channel count, and therefore cannot be diffed
    pixel-for-pixel."""


class InvalidComparisonInputError(DeepLearningVisionError):
    """Raised when the pair of VisualSnapshots supplied to a comparison
    run is not comparable (for example, belonging to different
    projects, or one snapshot supplying image/layout data that the
    other omits)."""
