from pathlib import Path

from .dataset import Dataset
from .names import DatasetName


def candidates_path(root: Path, source: DatasetName, target: DatasetName) -> Path:
    """Where the candidates between two datasets are stored, inside the datasets folder `root`."""
    return Path(root) / "03_candidate_generation" / source.folder / f"{source.label}_{target.label}.json".lower()


class CandidateSet:
    """The candidates between two datasets (written by candidate_generation/export_candidates.py).

        kima_yaqut = TestSetLoader().load_candidates(TestSetName.MEHDIE)[0]
        kima_yaqut.candidates["138113"]              # ["4521", ...]  target ids, best score first
        kima_yaqut.links                             # ground truth {(source_id, target_id), ...}
        for record, candidates in kima_yaqut:        # a Record and its candidate Records
            ...
    """

    def __init__(self, source: Dataset, target: Dataset, candidates: dict[str, list[str]], links=frozenset()):
        self.source = source
        self.target = target
        self.candidates = candidates
        self.links = set(links)

    def __iter__(self):
        for source_id, target_ids in self.candidates.items():
            yield self.source[source_id], [self.target[target_id] for target_id in target_ids]
