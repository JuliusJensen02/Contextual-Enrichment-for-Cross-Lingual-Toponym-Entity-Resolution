"""DeepER entity-matching implementation."""

from .deeper import (
    FEATURE_NAMES,
    DeepERFeatureExtractor,
    compare_records,
    load_classifier,
    match_probability,
    train_classifier,
)

__all__ = [
    "FEATURE_NAMES",
    "DeepERFeatureExtractor",
    "compare_records",
    "load_classifier",
    "match_probability",
    "train_classifier",
]
