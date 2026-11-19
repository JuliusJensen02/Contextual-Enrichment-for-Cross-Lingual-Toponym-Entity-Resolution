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
    add the best ones of every linked record to its set.

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
SPLIT = (0.6, 0.2, 0.2)  # train, validation, test
NEGATIVES_PER_RECORD = 20
SEED = 13

CANDIDATE_SETS = [TestSetName.MEHDIE, TestSetName.PLEIADES_TRISMEGISTOS, TestSetName.WIKIDATA_ZH_RU]
HARD_NEGATIVES_PER_RECORD = -1 # -1 = every record to all entities

class EntityPair:
    def __init__(self, src_id: str, target_id: str, match: bool):
        self.src_id = src_id
        self.target_id = target_id
        self.match = match


def EntityPair_from_list(source_id: str, target_ids: list[str], match: bool) -> list[EntityPair]:
    return [EntityPair(source_id, target_id, match) for target_id in target_ids]

def random_split_list_n(lst: list, splits: tuple[float, float, float]) -> list[list]:
    """Randomises a list, then splits it into n parts, where the sizes of the parts are given in splits."""
    assert sum(splits) == 1, f"sum(splits)={sum(splits)} != 1"
    result = []
    start = 0
    random.Random(SEED).shuffle(lst)
    for size in splits:
        result.append(lst[start:start + size])
        start += size
    return result


if __name__ == "__main__":
    for candidates_set_name in CANDIDATE_SETS:
        train_set, validation_set, test_set = [], [], []
        for candidate_set in TestSetLoader().load_candidates(candidates_set_name):
            for source_id in candidate_set.candidates.keys():
                positive_candidates, negative_candidates = candidate_set.split_candidates(source_id)
                n = len(positive_candidates) + len(negative_candidates)
                if len(train_set) + n < SPLIT[0] * candidate_set.amount_of_candidates:
                    train_set += EntityPair_from_list(source_id, positive_candidates, True)
                    train_set += EntityPair_from_list(source_id, negative_candidates, False)
                elif len(validation_set) + n < SPLIT[1] * candidate_set.amount_of_candidates:
                    validation_set += EntityPair_from_list(source_id, positive_candidates, True)
                    validation_set += EntityPair_from_list(source_id, negative_candidates, False)
                else:
                    test_set += EntityPair_from_list(source_id, positive_candidates, True)
                    test_set += EntityPair_from_list(source_id, negative_candidates, False)
        print(
            f"{candidates_set_name.name}: {len(train_set)} train, {len(validation_set)} validation, {len(test_set)} test")
