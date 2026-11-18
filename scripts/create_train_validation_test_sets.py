"""Splits every test set into a training, validation and test set and writes them to
datasets/04_train_validation_test/<test set>/{train,validation,test}.tsv, one row per pair:

  group, source_dataset, source_id, target_dataset, target_id, label     (1 = match, 0 = no match)

The split is made on entities, not on pairs. An entity is a group of records that the ground
truth links together, so all pairs of one place end up in the same set.

The negatives come from one of two places:
  - MEHDIE has them in its ground truth file (the rows that are not "same_as"). The two records
    of such a row are kept in the same set, so none of these pairs is lost in the split.
  - The other test sets only list matches. There we assume that a candidate from candidate
    generation (datasets/03_candidate_generation/) that is not the match is a negative, and
    add the best ones to the training and validation set.

  python scripts/create_train_validation_test_sets.py
"""
import random
import sys
from pathlib import Path

import networkx as nx
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))  # the repo root, for data_loader

from data_loader import TestSetLoader, TestSetName  # noqa: E402

OUT_DIR = Path(__file__).resolve().parents[1] / "datasets" / "04_train_validation_test"
TRAIN_SHARE = 0.6
VALIDATION_SHARE = 0.2  # the rest is the test set
NEGATIVES_PER_RECORD = 5
SEED = 13

# A record is (dataset, record id) and a pair is (record, record).


def find_groups(pairs):
    """{record: group number}. Records are in the same group when they are connected by the
    pairs, directly or through other records."""
    graph = nx.Graph()
    graph.add_edges_from(pairs)
    groups = sorted(sorted(group) for group in nx.connected_components(graph))
    return {record: number for number, group in enumerate(groups) for record in group}


def split_groups(group_of):
    """{record: "train" / "validation" / "test"}. The groups are shuffled and divided, and
    every record gets the set of its group."""
    numbers = sorted(set(group_of.values()))
    random.Random(SEED).shuffle(numbers)
    n_train = round(len(numbers) * TRAIN_SHARE)
    n_validation = round(len(numbers) * VALIDATION_SHARE)
    split_of_group = {}
    for position, number in enumerate(numbers):
        if position < n_train:
            split_of_group[number] = "train"
        elif position < n_train + n_validation:
            split_of_group[number] = "validation"
        else:
            split_of_group[number] = "test"
    return {record: split_of_group[number] for record, number in group_of.items()}


def labelled_negatives(truth, source, target):
    """The pairs between two datasets that the ground truth says are not a match. The file
    lists them in both directions, here they all go from source to target."""
    rows = truth[truth["link_type"] != "same_as"]
    forward = rows[(rows["source_dataset"] == source) & (rows["target_dataset"] == target)]
    backward = rows[(rows["source_dataset"] == target) & (rows["target_dataset"] == source)]
    pairs = set(zip(forward["source_place_id"], forward["target_place_id"]))
    pairs |= set(zip(backward["target_place_id"], backward["source_place_id"]))
    return [((source, source_id), (target, target_id)) for source_id, target_id in sorted(pairs)]


def candidate_negatives(candidate_set, entity_of, split_of):
    """For every linked source record in training and validation: its best candidates that are
    not the same place. A candidate that belongs to another set is skipped."""
    source, target = candidate_set.source.label, candidate_set.target.label
    negatives = []
    for source_id in sorted({source_id for source_id, _ in candidate_set.links}):
        record = (source, source_id)
        if split_of[record] == "test":
            continue
        found = 0
        for target_id in candidate_set.candidates[source_id]:
            candidate = (target, target_id)
            in_other_set = candidate in split_of and split_of[candidate] != split_of[record]
            if found < NEGATIVES_PER_RECORD and not same_entity(record, candidate, entity_of) and not in_other_set:
                negatives.append((record, candidate))
                found += 1
    return negatives


def same_entity(record_1, record_2, entity_of):
    return record_1 in entity_of and entity_of[record_1] == entity_of.get(record_2)


def main():
    loader = TestSetLoader()
    for name in TestSetName:
        test_set = loader.load(name)
        candidate_sets = loader.load_candidates(name)

        matches, negatives = [], []
        for candidate_set in candidate_sets:
            source, target = candidate_set.source.label, candidate_set.target.label
            matches += [((source, source_id), (target, target_id))
                        for source_id, target_id in sorted(candidate_set.links)]
            negatives += labelled_negatives(test_set.ground_truth.frame, source, target)

        entity_of = find_groups(matches)
        group_of = find_groups(matches + negatives)  # without labelled negatives a group is an entity
        split_of = split_groups(group_of)

        if negatives:
            negatives = [pair for pair in negatives if not same_entity(*pair, entity_of)]
        else:
            for candidate_set in candidate_sets:
                negatives += candidate_negatives(candidate_set, entity_of, split_of)

        rows = [[split_of[source], group_of[source], *source, *target, label]
                for pairs, label in [(matches, 1), (negatives, 0)] for source, target in pairs]
        columns = ["split", "group", "source_dataset", "source_id", "target_dataset", "target_id", "label"]
        pairs = pd.DataFrame(rows, columns=columns)

        folder = OUT_DIR / test_set.datasets[0].name.folder
        folder.mkdir(parents=True, exist_ok=True)
        print(f"{name.name}: {len(set(entity_of.values()))} entities")
        for split in ["train", "validation", "test"]:
            part = pairs[pairs["split"] == split].drop(columns="split")
            part.to_csv(folder / f"{split}.tsv", sep="\t", index=False)
            print(f"  {split:10s} {(part['label'] == 1).sum():5d} matches, {(part['label'] == 0).sum():5d} negatives")


if __name__ == "__main__":
    main()
