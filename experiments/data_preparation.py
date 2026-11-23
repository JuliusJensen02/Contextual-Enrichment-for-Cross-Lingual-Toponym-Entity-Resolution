"""Data preparation for matching methods.

Reads the labelled candidates of a split (datasets/04_train_validation_test/<test set>/<split>.tsv,
one row per query-candidate with columns source_dataset, source_id, target_dataset, target_id, label),
fills in the full records from datasets/02_minimized_datasets, and keeps only the requested attribute
categories. Full records are cached per dataset, so changing the categories between experiments is cheap.
"""
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple, Optional

import pandas as pd

from data_loader import DatasetName, Record, TestSetName

DATASETS_ROOT = Path(__file__).resolve().parents[1] / "datasets"
DATASET_TYPES = ("train", "validation", "test")
_DATASETS_BY_LABEL = {dataset.label: dataset for dataset in DatasetName}

# Record fields per attribute category, for each dataset
_BASE_CATEGORIES = {
    "name_variants":    ["title_ipa", "name_variants"],
    "absolute":         ["lat", "lon"],
    "relation":         ["country"],
    "temporal":         ["begin_date", "end_date"],
    "classification":   ["types"],
}
_WIKI_CATEGORIES = {
    "name_variants":    ["title_ipa", "name_variants", "wiki_title"],
    "absolute":         ["lat", "lon"],
    "relation":         ["country", "capital", "neighbours", "population"],
    "temporal":         ["inception", "dissolved"],
    "classification":   ["instance_of_label"],
    "description":      ["description", "described_by"],
}
DATASET_CATEGORIES = {
    DatasetName.KIMA:         {**_BASE_CATEGORIES, "description": ["description"]},
    DatasetName.THURAYYA:     {**_BASE_CATEGORIES, "description": ["description"]},
    DatasetName.YAQUT:        {**_BASE_CATEGORIES, "description": ["description"]},
    DatasetName.PLEIADES:     {**_BASE_CATEGORIES, "description": ["details", "description"]},
    DatasetName.TRISMEGISTOS: {**_BASE_CATEGORIES, "description": ["text_snippets"]},
    DatasetName.WIKIDATA_RU:  _WIKI_CATEGORIES,
    DatasetName.WIKIDATA_ZH:  _WIKI_CATEGORIES,
}
AVAILABLE_CATEGORIES = {"name_variants", "absolute", "relation", "temporal", "classification", "description"}


class Pair(NamedTuple):
    """A query record and its candidates; `labels[i]` is True when `candidates[i]` is a golden link."""
    query: Record
    candidates: list[Record]
    labels: list[bool] = []


@lru_cache(maxsize=16)
def _load_records(dataset: DatasetName) -> dict[str, Record]:
    """All records of a dataset with all their fields, by id."""
    path = DATASETS_ROOT / "02_minimized_datasets" / dataset.folder / dataset.file
    rows = pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    records = (Record.from_row(dataset, row) for row in rows.to_dict("records"))
    return {record.id: record for record in records}


def _read_split(test_set: TestSetName, dataset_type: str) -> pd.DataFrame:
    """The labelled candidate rows of one split of a test set."""
    if dataset_type not in DATASET_TYPES:
        raise ValueError(f"Invalid dataset_type '{dataset_type}'. Valid: {list(DATASET_TYPES)}")
    path = DATASETS_ROOT / "04_train_validation_test" / test_set.datasets[0].folder / f"{dataset_type}.tsv"
    return pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False, encoding="utf-8-sig")


def _build_pairs(rows: pd.DataFrame) -> list[Pair]:
    """One Pair per (source dataset, source id, target dataset), in file order."""
    pairs: dict[tuple[str, str, str], Pair] = {}
    columns = ["source_dataset", "source_id", "target_dataset", "target_id", "label"]
    for source_label, source_id, target_label, target_id, label in zip(*(rows[c] for c in columns)):
        targets = _load_records(_DATASETS_BY_LABEL[target_label])
        key = (source_label, source_id, target_label)
        if key not in pairs:
            sources = _load_records(_DATASETS_BY_LABEL[source_label])
            pairs[key] = Pair(sources[source_id], [], [])
        pairs[key].candidates.append(targets[target_id])
        pairs[key].labels.append(label == "1")
    return list(pairs.values())


def _keep_categories(record: Record, categories: list[str]) -> Record:
    """A copy of the record with only id, title and the fields of the given categories."""
    dataset_categories = DATASET_CATEGORIES[record.dataset]
    fields = {"id", "title"}
    for category in categories:
        fields.update(dataset_categories.get(category, []))
    return Record.from_row(record.dataset, {field: getattr(record, field) for field in fields})


class DataLoader:
    """Loads the labelled Pairs of one split of a test set, restricted to the given attribute categories.

    source_dataset / target_dataset optionally restrict the queries / candidates to one dataset.

        pairs = DataLoader(TestSetName.MEHDIE, ["name_variants", "absolute"], "test",
                           source_dataset=DatasetName.KIMA, target_dataset=DatasetName.YAQUT).load()
    """

    def __init__(
        self,
        test_set: TestSetName,
        attribute_categories: list[str],
        dataset_type: str = "test",
        source_dataset: Optional[DatasetName] = None,
        target_dataset: Optional[DatasetName] = None,
    ):
        for category in attribute_categories:
            if category not in AVAILABLE_CATEGORIES:
                raise ValueError(f"Invalid category '{category}'. Valid: {sorted(AVAILABLE_CATEGORIES)}")
        if dataset_type not in DATASET_TYPES:
            raise ValueError(f"Invalid dataset_type '{dataset_type}'. Valid: {list(DATASET_TYPES)}")

        self.test_set = test_set
        self.attribute_categories = attribute_categories
        self.dataset_type = dataset_type
        self.source_dataset = source_dataset
        self.target_dataset = target_dataset

    def load(self) -> list[Pair]:
        rows = _read_split(self.test_set, self.dataset_type)
        if self.source_dataset:
            rows = rows[rows["source_dataset"] == self.source_dataset.label]
        if self.target_dataset:
            rows = rows[rows["target_dataset"] == self.target_dataset.label]

        pairs = _build_pairs(rows)
        if not self.attribute_categories:
            return pairs

        filtered = []
        for pair in pairs:
            query = _keep_categories(pair.query, self.attribute_categories)
            candidates = [_keep_categories(candidate, self.attribute_categories) for candidate in pair.candidates]
            filtered.append(Pair(query, candidates, pair.labels))
        return filtered


def load_pairs(
    test_set: TestSetName,
    source_dataset: Optional[DatasetName] = None,
    target_dataset: Optional[DatasetName] = None,
    attribute_categories: Optional[list[str]] = None,
    dataset_type: str = "test",
) -> list[Pair]:
    """The labelled Pairs of one split, for any matching method (bi-encoder, Ditto, LLMs).

        pairs = load_pairs(TestSetName.MEHDIE, DatasetName.KIMA, DatasetName.YAQUT,
                           ["name_variants", "absolute"], dataset_type="test")
        for pair in pairs:
            for candidate, is_match in zip(pair.candidates, pair.labels):
                ...
    """
    loader = DataLoader(test_set, attribute_categories or [], dataset_type, source_dataset, target_dataset)
    return loader.load()