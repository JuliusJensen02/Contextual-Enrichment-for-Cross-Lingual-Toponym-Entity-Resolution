from math import isclose
from types import SimpleNamespace

import numpy as np
import pytest

from Methods.deepER.run_deeper import evaluate_pairs, select_f5_threshold
from experiments.data_preparation import Pair


class FirstFeatureExtractor:
    def prepare_pairs(self, pairs):
        pass

    def compare(self, query, candidate):
        return [float(candidate.score)]


class ThresholdClassifier:
    def predict_proba(self, features):
        probabilities = features[:, 0]
        return np.column_stack((1.0 - probabilities, probabilities))


def test_evaluate_pairs_reports_candidate_metrics_and_outputs():
    pairs = [
        Pair(
            query=SimpleNamespace(id="source-1"),
            candidates=[
                SimpleNamespace(id="target-match", score=0.9),
                SimpleNamespace(id="target-negative", score=0.1),
            ],
            labels=[True, False],
        )
    ]

    metrics, predictions = evaluate_pairs(
        pairs,
        ThresholdClassifier(),
        threshold=0.5,
        extractor=FirstFeatureExtractor(),
    )

    assert metrics == {
        "pairs": 2,
        "true_positives": 1,
        "false_positives": 0,
        "false_negatives": 0,
        "true_negatives": 1,
        "precision": 1.0,
        "recall": 1.0,
        "f1": 1.0,
        "f5": 1.0,
        "accuracy": 1.0,
    }
    assert {key: predictions[0][key] for key in ("source_id", "target_id", "label", "match")} == {
        "source_id": "source-1",
        "target_id": "target-match",
        "label": 1,
        "match": 1,
    }
    assert isclose(predictions[0]["probability"], 0.9, rel_tol=1e-6)


def test_evaluate_pairs_rejects_misaligned_labels():
    pair = Pair(
        query=SimpleNamespace(id="source-1"),
        candidates=[SimpleNamespace(id="target-1", score=0.9)],
        labels=[],
    )

    with pytest.raises(ValueError, match="candidates but 0 labels"):
        evaluate_pairs([pair], ThresholdClassifier(), threshold=0.5, extractor=FirstFeatureExtractor())


def test_evaluate_pairs_rejects_empty_splits():
    with pytest.raises(ValueError, match="at least one labeled candidate"):
        evaluate_pairs([], ThresholdClassifier(), threshold=0.5, extractor=FirstFeatureExtractor())


def test_select_f5_threshold_prefers_recall_on_validation():
    pairs = [
        Pair(
            query=SimpleNamespace(id="source-1"),
            candidates=[
                SimpleNamespace(id="match-high", score=0.9),
                SimpleNamespace(id="negative-1", score=0.8),
                SimpleNamespace(id="negative-2", score=0.7),
                SimpleNamespace(id="negative-3", score=0.6),
                SimpleNamespace(id="negative-4", score=0.5),
                SimpleNamespace(id="match-low", score=0.4),
            ],
            labels=[True, False, False, False, False, True],
        )
    ]

    threshold, metrics = select_f5_threshold(
        pairs,
        ThresholdClassifier(),
        extractor=FirstFeatureExtractor(),
    )

    assert threshold == pytest.approx(0.4)
    assert metrics["f5"] > metrics["f1"]
    assert metrics["true_positives"] == 2
    assert metrics["false_positives"] == 4


def test_select_f5_threshold_requires_both_validation_classes():
    pairs = [
        Pair(
            query=SimpleNamespace(id="source-1"),
            candidates=[SimpleNamespace(id="target-1", score=0.9)],
            labels=[True],
        )
    ]

    with pytest.raises(ValueError, match="both match and non-match"):
        select_f5_threshold(
            pairs,
            ThresholdClassifier(),
            extractor=FirstFeatureExtractor(),
        )
