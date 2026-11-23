from types import SimpleNamespace

from experiments.metrics import (
    calculate_metrics,
    candidate_predictions,
    llm_predictions,
    normalize_pairs,
)


def test_calculate_metrics_with_perfect_predictions():
    metrics = calculate_metrics(
        predicted_pairs={("k1", "y1"), ("k2", "y2")},
        true_pairs={("k1", "y1"), ("k2", "y2")},
    )

    assert metrics["true_positives"] == 2
    assert metrics["false_positives"] == 0
    assert metrics["false_negatives"] == 0
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1"] == 1.0


def test_calculate_metrics_counts_missed_and_extra_matches():
    metrics = calculate_metrics(
        predicted_pairs={("k1", "y1"), ("k2", "y3")},
        true_pairs={("k1", "y1"), ("k2", "y2")},
    )

    assert metrics["true_positives"] == 1
    assert metrics["false_positives"] == 1
    assert metrics["false_negatives"] == 1
    assert metrics["precision"] == 0.5
    assert metrics["recall"] == 0.5
    assert metrics["f1"] == 0.5


def test_calculate_metrics_handles_empty_predictions():
    metrics = calculate_metrics(set(), {("k1", "y1")})

    assert metrics["precision"] == 0.0
    assert metrics["recall"] == 0.0
    assert metrics["f1"] == 0.0


def test_normalize_project_dataset_id_pairs():
    pairs = {
        (("KIMA", "k1"), ("YAQUT", "y1")),
        (("KIMA", "k2"), ("YAQUT", "y2")),
    }

    assert normalize_pairs(pairs) == {("k1", "y1"), ("k2", "y2")}


def test_llm_predictions_convert_candidate_numbers():
    pairs = [
        SimpleNamespace(
            query=SimpleNamespace(id="k1"),
            candidates=[
                SimpleNamespace(id="y1"),
                SimpleNamespace(id="y2"),
            ],
        ),
        SimpleNamespace(
            query=SimpleNamespace(id="k2"),
            candidates=[SimpleNamespace(id="y3")],
        ),
    ]

    assert llm_predictions(pairs, [2, 0]) == {("k1", "y2")}


def test_candidate_predictions_support_ditto_candidate_ids():
    pairs = [
        SimpleNamespace(
            query=SimpleNamespace(id="k1"),
            candidates=[SimpleNamespace(id="y1"), SimpleNamespace(id="y2")],
        )
    ]
    results = [
        [
            {"candidate": "y1", "match": False, "probability": 0.2},
            {"candidate": "y2", "match": True, "probability": 0.8},
        ]
    ]

    assert candidate_predictions(pairs, results) == {("k1", "y2")}


def test_candidate_predictions_support_bi_encoder_result_order():
    pairs = [
        SimpleNamespace(
            query=SimpleNamespace(id="k1"),
            candidates=[SimpleNamespace(id="y1"), SimpleNamespace(id="y2")],
        )
    ]
    results = [
        [
            {"match": True, "probability": 0.8},
            {"match": False, "probability": 0.2},
        ]
    ]

    assert candidate_predictions(pairs, results) == {("k1", "y1")}
