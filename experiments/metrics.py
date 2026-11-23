"""Precision, recall, F1, and confusion-matrix metrics for entity matching."""

from collections.abc import Iterable


def normalize_pairs(pairs: Iterable) -> set[tuple[str, str]]:
    """Normalize project links or (source_id, target_id) pairs."""
    normalized = set()
    for pair in pairs:
        if len(pair) != 2:
            raise ValueError("Each pair must contain a source and target")

        source, target = pair

        if not isinstance(source, str) and hasattr(source, "dataset"):
            source = getattr(source, "id", None)
        elif not isinstance(source, str) and isinstance(source, tuple) and len(source) == 2:
            source = source[1]

        if not isinstance(target, str) and hasattr(target, "dataset"):
            target = getattr(target, "id", None)
        elif not isinstance(target, str) and isinstance(target, tuple) and len(target) == 2:
            target = target[1]

        if source is None or target is None:
            raise ValueError("Record pairs must contain usable source and target IDs")
        normalized.add((str(source), str(target)))

    return normalized


def calculate_metrics(
    predicted_pairs: Iterable,
    true_pairs: Iterable,
) -> dict[str, float | int]:
    """Calculate match metrics from sets of (source_id, target_id) pairs."""
    predicted = normalize_pairs(predicted_pairs)
    true = normalize_pairs(true_pairs)

    true_positives = len(predicted & true)
    false_positives = len(predicted - true)
    false_negatives = len(true - predicted)

    precision = (
        true_positives / (true_positives + false_positives)
        if true_positives + false_positives
        else 0.0
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if true_positives + false_negatives
        else 0.0
    )
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )

    return {
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def llm_predictions(pairs, candidate_numbers: Iterable[int]) -> set[tuple[str, str]]:
    """Convert LLM candidate numbers into (source_id, target_id) pairs."""
    predicted = set()

    for pair, candidate_number in zip(pairs, candidate_numbers):
        if isinstance(candidate_number, int) and 1 <= candidate_number <= len(pair.candidates):
            candidate = pair.candidates[candidate_number - 1]
            predicted.add((pair.query.id, candidate.id))

    return predicted


def candidate_predictions(
    pairs,
    candidate_results: Iterable[Iterable[dict]],
) -> set[tuple[str, str]]:
    """Convert bi-encoder or Ditto result dictionaries into matching pairs."""
    predicted = set()

    for pair, results in zip(pairs, candidate_results):
        candidate_ids = {candidate.id for candidate in pair.candidates}

        for index, result in enumerate(results):
            candidate_id = result.get("candidate")
            if candidate_id is None:
                candidate_id = result.get("id")
            if candidate_id is None and index < len(pair.candidates):
                candidate_id = pair.candidates[index].id

            if result.get("match") is True and str(candidate_id) in candidate_ids:
                predicted.add((pair.query.id, str(candidate_id)))

    return predicted


def get_ground_truth_links(
    test_set,
    source_dataset,
    target_dataset,
) -> set[tuple[str, str]]:
    """Read ground-truth links for one source/target dataset pair."""
    return test_set.links_between(source_dataset, target_dataset)
