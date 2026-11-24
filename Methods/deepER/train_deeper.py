"""Train DeepER from the project's labelled candidate-pair training split."""

import argparse
from pathlib import Path

import joblib

from data_loader import DatasetName, TestSetName
from experiments import load_pairs
from Methods.deepER.deeper import FEATURE_NAMES, train_classifier


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test-set", choices=[value.name for value in TestSetName], required=True)
    parser.add_argument("--source-dataset", choices=[value.name for value in DatasetName], required=True)
    parser.add_argument("--target-dataset", choices=[value.name for value in DatasetName], required=True)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("Methods/deepER/deeper_model.joblib"),
        help="Path for the trained classifier.",
    )
    args = parser.parse_args()

    pairs = load_pairs(
        TestSetName[args.test_set],
        DatasetName[args.source_dataset],
        DatasetName[args.target_dataset],
        dataset_type="train",
    )
    if not pairs:
        raise SystemExit("No training pairs found for the selected test set and dataset direction.")

    classifier = train_classifier(pairs)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(classifier, args.out)

    total = sum(len(pair.labels) for pair in pairs)
    positives = sum(sum(pair.labels) for pair in pairs)
    print(f"Trained on {total} pairs ({positives} matches, {total - positives} non-matches).")
    print(f"Features: {', '.join(FEATURE_NAMES)}")
    print(f"Saved classifier to {args.out}")


if __name__ == "__main__":
    main()
