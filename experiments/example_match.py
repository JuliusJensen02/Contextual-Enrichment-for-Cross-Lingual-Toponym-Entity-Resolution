"""Example end-to-end matching experiment using all three matching methods."""

import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_loader import DatasetName, TestSetLoader, TestSetName
from experiments import load_pairs
from experiments.matching import call_matching_methods, load_ditto_model
from experiments.metrics import (
    calculate_metrics,
    candidate_predictions,
    llm_predictions,
)


TEST_SET = TestSetName.MEHDIE
SOURCE_DATASET = DatasetName.KIMA
TARGET_DATASET = DatasetName.YAQUT
ATTRIBUTE_CATEGORIES = ["name_variants", "absolute"]
LLM_PROVIDER = "llama"
BI_ENCODER_MODEL = "path/to/gradientboost-model.json"
DEEPER_MODEL = "path/to/deeper-model.joblib"
DITTO_CHECKPOINT_PATH = "checkpoints"
DITTO_TASK = "toponym_experiment"
DITTO_LM = "distilbert"
BI_ENCODER_THRESHOLD = 0.5
DEEPER_THRESHOLD = 0.5
DITTO_THRESHOLD = 0.5


def main() -> None:
    test_set = TestSetLoader().load(TEST_SET)

    pairs = load_pairs(
        test_set=TEST_SET,
        source_dataset=SOURCE_DATASET,
        target_dataset=TARGET_DATASET,
        attribute_categories=ATTRIBUTE_CATEGORIES,
    )

    # Load the trained local models once, before dispatching across all pairs.
    from Methods.bi_encoder.bi_encoder import load_classifier
    from Methods.deepER.deeper import load_classifier as load_deeper_classifier

    classifier = load_classifier(BI_ENCODER_MODEL)
    deeper_classifier = load_deeper_classifier(DEEPER_MODEL)
    ditto_model = load_ditto_model(
        checkpoint_path=DITTO_CHECKPOINT_PATH,
        task=DITTO_TASK,
        lm=DITTO_LM,
        use_gpu=True,
    )

    results = call_matching_methods(
        pairs,
        methods=("llm", "bi_encoder", "deeper", "ditto"),
        classifier=classifier,
        deeper_classifier=deeper_classifier,
        ditto_model=ditto_model,
        llm_provider=LLM_PROVIDER,
        bi_encoder_threshold=BI_ENCODER_THRESHOLD,
        deeper_threshold=DEEPER_THRESHOLD,
        ditto_threshold=DITTO_THRESHOLD,
        ditto_lm=DITTO_LM,
    )

    true_pairs = test_set.links_between(SOURCE_DATASET, TARGET_DATASET)

    print(f"Loaded {len(pairs)} query-candidate pairs")
    print(f"Ground-truth matches: {len(true_pairs)}")

    predicted_by_method = {
        "llm": llm_predictions(pairs, results["llm"]),
        "bi_encoder": candidate_predictions(pairs, results["bi_encoder"]),
        "deeper": candidate_predictions(pairs, results["deeper"]),
        "ditto": candidate_predictions(pairs, results["ditto"]),
    }

    for method, predicted_pairs in predicted_by_method.items():
        metrics = calculate_metrics(predicted_pairs, true_pairs)
        print(
            f"{method}: "
            f"predicted={len(predicted_pairs)}, "
            f"precision={metrics['precision']:.3f}, "
            f"recall={metrics['recall']:.3f}, "
            f"F1={metrics['f1']:.3f}"
        )


if __name__ == "__main__":
    main()
