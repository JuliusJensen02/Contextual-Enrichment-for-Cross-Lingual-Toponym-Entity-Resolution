"""Train, evaluate, and optionally save a DeepER model in one command."""

import argparse
import csv
import math
from pathlib import Path

import numpy as np

from data_loader import DatasetName, TestSetName
from experiments import load_pairs
from Methods.deepER.deeper import DeepERFeatureExtractor, train_classifier


def _score_pairs(pairs, classifier, extractor=None):
    """Score labeled candidate pairs without applying a decision threshold."""
    extractor = extractor or DeepERFeatureExtractor()
    extractor.prepare_pairs(pairs)
    feature_rows = []
    pair_rows = []

    for pair in pairs:
        if len(pair.candidates) != len(pair.labels):
            raise ValueError(
                f"Pair for query {pair.query.id!r} has {len(pair.candidates)} candidates "
                f"but {len(pair.labels)} labels."
            )
        for candidate, label in zip(pair.candidates, pair.labels):
            feature_rows.append(extractor.compare(pair.query, candidate))
            pair_rows.append((pair.query.id, candidate.id, int(bool(label))))

    if not feature_rows:
        raise ValueError("Evaluation requires at least one labeled candidate pair.")
    probabilities = classifier.predict_proba(np.asarray(feature_rows, dtype=np.float32))[:, 1]
    return [
        {
            "source_id": source_id,
            "target_id": target_id,
            "label": label,
            "probability": float(probability),
        }
        for (source_id, target_id, label), probability in zip(pair_rows, probabilities)
    ]


def _metrics_at_threshold(predictions, threshold: float):
    true_positives = false_positives = false_negatives = true_negatives = 0
    evaluated = []
    for prediction in predictions:
        predicted = prediction["probability"] >= threshold
        actual = bool(prediction["label"])
        if predicted and actual:
            true_positives += 1
        elif predicted:
            false_positives += 1
        elif actual:
            false_negatives += 1
        else:
            true_negatives += 1
        evaluated.append({**prediction, "match": int(predicted)})

    precision = true_positives / (true_positives + false_positives) if true_positives + false_positives else 0.0
    recall = true_positives / (true_positives + false_negatives) if true_positives + false_negatives else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    beta_squared = 25
    f5_denominator = beta_squared * precision + recall
    f5 = (1 + beta_squared) * precision * recall / f5_denominator if f5_denominator else 0.0
    total = true_positives + false_positives + false_negatives + true_negatives
    return {
        "pairs": total,
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "true_negatives": true_negatives,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "f5": f5,
        "accuracy": (true_positives + true_negatives) / total,
    }, evaluated


def evaluate_pairs(pairs, classifier, threshold: float, extractor=None):
    """Score labeled candidate pairs and return metrics plus per-candidate output rows."""
    predictions = _score_pairs(pairs, classifier, extractor)
    return _metrics_at_threshold(predictions, threshold)


def select_f5_threshold(pairs, classifier, extractor=None) -> tuple[float, dict]:
    """Select the threshold with highest validation F5; break ties by recall, then precision."""
    predictions = _score_pairs(pairs, classifier, extractor)
    positives = sum(prediction["label"] for prediction in predictions)
    if positives == 0 or positives == len(predictions):
        raise ValueError("Validation split must contain both match and non-match labels to tune threshold.")
    ordered = sorted(predictions, key=lambda prediction: prediction["probability"], reverse=True)
    true_positives = false_positives = 0
    best_threshold = ordered[0]["probability"]
    best_key = (-1.0, -1.0, -1.0, -1.0)
    index = 0
    while index < len(ordered):
        threshold = ordered[index]["probability"]
        while index < len(ordered) and ordered[index]["probability"] == threshold:
            if ordered[index]["label"]:
                true_positives += 1
            else:
                false_positives += 1
            index += 1

        false_negatives = positives - true_positives
        precision = true_positives / (true_positives + false_positives)
        recall = true_positives / positives
        beta_squared = 25
        f5_denominator = beta_squared * precision + recall
        f5 = (1 + beta_squared) * precision * recall / f5_denominator if f5_denominator else 0.0
        key = (f5, recall, precision, threshold)
        if key > best_key:
            best_key = key
            best_threshold = threshold

    metrics, _ = _metrics_at_threshold(predictions, best_threshold)
    return best_threshold, metrics


def _write_predictions(path: Path, predictions) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=predictions[0].keys(), delimiter="\t")
        writer.writeheader()
        writer.writerows(predictions)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test-set", choices=[value.name for value in TestSetName], default="MEHDIE")
    parser.add_argument("--source-dataset", choices=[value.name for value in DatasetName], default="KIMA")
    parser.add_argument("--target-dataset", choices=[value.name for value in DatasetName], default="YAQUT")
    parser.add_argument(
        "--threshold",
        type=float,
        help="Override the threshold selected by maximum F5 on validation.tsv.",
    )
    parser.add_argument("--save-model", type=Path, help="Optionally save the trained classifier.")
    parser.add_argument("--predictions-out", type=Path, help="Optionally write test predictions as TSV.")
    args = parser.parse_args()
    if args.threshold is not None and (
        not math.isfinite(args.threshold) or not 0.0 <= args.threshold <= 1.0
    ):
        parser.error("--threshold must be a finite number between 0 and 1.")

    test_set = TestSetName[args.test_set]
    source_dataset = DatasetName[args.source_dataset]
    target_dataset = DatasetName[args.target_dataset]
    pairs_for = {
        split: load_pairs(
            test_set,
            source_dataset,
            target_dataset,
            dataset_type=split,
        )
        for split in ("train", "validation", "test")
    }

    train_pairs = pairs_for["train"]
    validation_pairs = pairs_for["validation"]
    test_pairs = pairs_for["test"]
    if not train_pairs:
        raise SystemExit("No training pairs found for the selected test set and dataset direction.")
    if not test_pairs:
        raise SystemExit("No test pairs found for the selected test set and dataset direction.")
    if not validation_pairs:
        raise SystemExit("No validation pairs found for the selected test set and dataset direction.")

    train_count = sum(len(pair.candidates) for pair in train_pairs)
    print(
        f"Training on {train_count:,} candidates from "
        f"{args.test_set} {args.source_dataset} -> {args.target_dataset}"
    )
    extractor = DeepERFeatureExtractor()
    print("Encoding training attributes in batches...")
    classifier = train_classifier(train_pairs, extractor=extractor, verbose=1)

    if args.threshold is None:
        threshold, validation_metrics = select_f5_threshold(
            validation_pairs,
            classifier,
            extractor=extractor,
        )
        print(
            f"Selected threshold on validation: {threshold:.6f} "
            f"(validation F5={validation_metrics['f5']:.3f})"
        )
    else:
        threshold = args.threshold
        validation_metrics, _ = evaluate_pairs(
            validation_pairs,
            classifier,
            threshold,
            extractor=extractor,
        )
        print(
            f"Using provided threshold: {threshold:.6f} "
            f"(validation F5={validation_metrics['f5']:.3f})"
        )

    metrics, predictions = evaluate_pairs(
        test_pairs,
        classifier,
        threshold,
        extractor=extractor,
    )
    print(f"Test candidates: {metrics['pairs']:,} (threshold={threshold:.6f})")
    print(
        f"Precision: {metrics['precision']:.3f} | Recall: {metrics['recall']:.3f} | "
        f"F5: {metrics['f5']:.3f} | F1: {metrics['f1']:.3f} | "
        f"Accuracy: {metrics['accuracy']:.3f}"
    )
    print(
        f"TP: {metrics['true_positives']:,} | FP: {metrics['false_positives']:,} | "
        f"FN: {metrics['false_negatives']:,} | TN: {metrics['true_negatives']:,}"
    )

    if args.save_model:
        import joblib

        args.save_model.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(classifier, args.save_model)
        print(f"Saved model: {args.save_model}")
    if args.predictions_out:
        _write_predictions(args.predictions_out, predictions)
        print(f"Saved predictions: {args.predictions_out}")


if __name__ == "__main__":
    main()
