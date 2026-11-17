import json
from functools import cached_property
from pathlib import Path

import pandas as pd

from .dataset import Dataset
from .names import DatasetName

FOLDER = "03_candidate_generation"


def candidates_path(root: Path, source: DatasetName, target: DatasetName) -> Path:
    """Where the candidates between two datasets are stored, inside the datasets folder `root`."""
    return Path(root) / FOLDER / source.folder / f"{source.label}_{target.label}.json".lower()


class CandidateSet:
    """The candidates between two datasets (written by candidate_generation/export_candidates.py):
    for every source record, the target records it may be the same place as.

        sets = TestSetLoader().load_candidates(TestSetName.MEHDIE)     # one CandidateSet per pair
        kima_yaqut = sets[0]
        kima_yaqut.source, kima_yaqut.target         # the two Datasets
        kima_yaqut.candidates["138113"]              # ["4521", ...]  target ids, best score first
        kima_yaqut.pairs                             # [(source_id, target_id), ...]
        kima_yaqut.links                             # the ground truth links between the two

        # the records themselves, with only the columns asked for (id is always included):
        for record, candidates in kima_yaqut.records(["title", "lat", "lon"]):
            record                                   # {"id": "138113", "title": ..., "lat": ..., "lon": ...}
            candidates                               # [{"id": "4521", "title": ..., ...}, ...]

        kima_yaqut.frame(["title"])     # one row per pair: source_id, source_title, target_id, target_title
        kima_yaqut.records(["title", "description"], target_columns=["title"])   # other columns for the target

    Without `columns`, every column of the dataset is included.
    """

    def __init__(self, source: Dataset, target: Dataset, candidates: dict[str, list[str]], links=frozenset()):
        self.source = source
        self.target = target
        self.candidates = candidates
        self.links = set(links)

    def __len__(self) -> int:
        return sum(map(len, self.candidates.values()))

    def __repr__(self) -> str:
        return (f"CandidateSet({self.source.name.name} -> {self.target.name.name}: {len(self.candidates)} records, "
                f"{len(self)} pairs)")

    @cached_property
    def pairs(self) -> list[tuple[str, str]]:
        """Every candidate pair as (source_id, target_id)."""
        return [(source_id, target_id) for source_id, targets in self.candidates.items() for target_id in targets]

    def records(self, columns=None, target_columns=None):
        """Yields (source record, [its candidate records]) for every source record, each record
        a dict of the chosen columns. `target_columns` defaults to `columns`."""
        source = _records(self.source, columns)
        target = _records(self.target, columns if target_columns is None else target_columns)
        for source_id, targets in self.candidates.items():
            yield source[source_id], [target[target_id] for target_id in targets]

    def frame(self, columns=None, target_columns=None) -> pd.DataFrame:
        """One row per candidate pair: the chosen columns of the source record (source_...) next
        to those of the target record (target_...)."""
        source = _table(self.source, columns).add_prefix("source_")
        target = _table(self.target, columns if target_columns is None else target_columns).add_prefix("target_")
        pairs = pd.DataFrame(self.pairs, columns=["source_id", "target_id"], dtype=str)
        merged = pairs.merge(source, on="source_id", how="left").merge(target, on="target_id", how="left")
        return merged[[*source.columns, *target.columns]]


def read_candidates(path: Path, source: Dataset, target: Dataset, links=frozenset()) -> CandidateSet:
    """The CandidateSet stored in one JSON file, for the two datasets it was made from."""
    data = json.loads(Path(path).read_text(encoding="utf8"))
    if (data["source"], data["target"]) != (source.label, target.label):
        raise ValueError(f"{path} holds {data['source']} -> {data['target']}, not {source.label} -> {target.label}")
    return CandidateSet(source, target, data["candidates"], links)


def _table(dataset: Dataset, columns) -> pd.DataFrame:
    """The dataset's table with the id and the chosen columns."""
    if columns is None:
        columns = dataset.frame.columns
    columns = [column for column in columns if column != "id"]
    missing = [column for column in columns if column not in dataset.frame.columns]
    if missing:
        raise KeyError(f"{dataset.label} has no column {missing}; it has {list(dataset.frame.columns)}")
    return dataset.frame[["id", *columns]]


def _records(dataset: Dataset, columns) -> dict[str, dict]:
    table = _table(dataset, columns)
    return dict(zip(table["id"], table.to_dict("records")))
