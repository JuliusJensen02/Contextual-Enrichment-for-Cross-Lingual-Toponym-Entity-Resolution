import csv
import random
from pathlib import Path

from data_loader import DatasetName, TestSetLoader, TestSetName  # noqa: E402

OUT_DIR = Path(__file__).resolve().parents[1] / "datasets" / "04_train_validation_test"
SPLIT = (0.6, 0.2, 0.2)  # train, validation, test
NEGATIVES_PER_RECORD = 20  # at most this many negatives per source record and candidate set, best score first
SEED = 42

CANDIDATE_SETS = [TestSetName.MEHDIE, TestSetName.PLEIADES_TRISMEGISTOS, TestSetName.WIKIDATA_ZH_RU]
HARD_NEGATIVES_PER_RECORD = -1 # -1 = every record to all entities

class EntityPair:
    def __init__(self, test_set: TestSetName, source_dataset: DatasetName, target_dataset: DatasetName,
                 src_id: str, target_id: str, match: bool):
        self.test_set = test_set
        self.source_dataset = source_dataset
        self.target_dataset = target_dataset
        self.src_id = src_id
        self.target_id = target_id
        self.match = match


def EntityPair_from_list(test_set: TestSetName, source_dataset: DatasetName, target_dataset: DatasetName,
                         source_id: str, target_ids: list[str], match: bool) -> list[EntityPair]:
    return [EntityPair(test_set, source_dataset, target_dataset, source_id, target_id, match)
            for target_id in target_ids]


def save_pairs(test_set: TestSetName, file_name: str, pairs: list[EntityPair]) -> None:
    """Writes the pairs to datasets/04_train_validation_test/<test set folder>/<file_name>.tsv."""
    folder = OUT_DIR / test_set.datasets[0].folder
    folder.mkdir(parents=True, exist_ok=True)
    with open(folder / f"{file_name}.tsv", "w", encoding="utf8", newline="") as file:
        writer = csv.writer(file, delimiter="\t")
        writer.writerow(["source_dataset", "source_id", "target_dataset", "target_id", "label"])
        for pair in pairs:
            writer.writerow([pair.source_dataset.label, pair.src_id, pair.target_dataset.label, pair.target_id,
                             int(pair.match)])


if __name__ == "__main__":
    for candidates_set_name in CANDIDATE_SETS:
        train_set, validation_set, test_set = [], [], []
        # All pairs of a source record, across the candidate sets, so a record never ends up in two sets.
        pairs_per_record = {}
        for candidate_set in TestSetLoader().load_candidates(candidates_set_name):
            source_dataset, target_dataset = candidate_set.source.name, candidate_set.target.name
            for source_id in candidate_set.candidates.keys():
                positive_candidates, negative_candidates = candidate_set.split_candidates(source_id)
                negative_candidates = negative_candidates[:NEGATIVES_PER_RECORD]
                pairs = pairs_per_record.setdefault((source_dataset, source_id), [])
                pairs += EntityPair_from_list(candidates_set_name, source_dataset, target_dataset,
                                              source_id, positive_candidates, True)
                pairs += EntityPair_from_list(candidates_set_name, source_dataset, target_dataset,
                                              source_id, negative_candidates, False)

        records = list(pairs_per_record.values())
        random.Random(SEED).shuffle(records)
        # Records with and without a match are split separately, so every set gets its share of the matches.
        with_match = [pairs for pairs in records if any(pair.match for pair in pairs)]
        without_match = [pairs for pairs in records if not any(pair.match for pair in pairs)]
        for group in (with_match, without_match):
            n_group = sum(len(pairs) for pairs in group)
            train_split, validation_split, test_split = [int(split * n_group) for split in SPLIT]
            n_inserted = 0
            for pairs in group:
                n = len(pairs)
                if n_inserted + n < train_split:
                    train_set += pairs
                elif n_inserted + n < train_split + validation_split:
                    validation_set += pairs
                else:
                    test_set += pairs
                n_inserted += n

        save_pairs(candidates_set_name, "train", train_set)
        save_pairs(candidates_set_name, "validation", validation_set)
        save_pairs(candidates_set_name, "test", test_set)
        print(
            f"{candidates_set_name.name}: {len(train_set)} train, {len(validation_set)} validation, {len(test_set)} test")

        train_positive = [pair for pair in train_set if pair.match]
        train_negative = [pair for pair in train_set if not pair.match]
        validation_positive = [pair for pair in validation_set if pair.match]
        validation_negative = [pair for pair in validation_set if not pair.match]
        test_positive = [pair for pair in test_set if pair.match]
        test_negative = [pair for pair in test_set if not pair.match]

        print(f"Train: {len(train_positive)} positive, {len(train_negative)} negative")
        print(f"Validation: {len(validation_positive)} positive, {len(validation_negative)} negative")
        print(f"Test: {len(test_positive)} positive, {len(test_negative)} negative")
