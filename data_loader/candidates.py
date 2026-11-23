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
        self.amount_of_candidates = sum(len(c) for c in candidates.values())

    def __iter__(self):
        for source_id, target_ids in self.candidates.items():
            yield self.source[source_id], [self.target[target_id] for target_id in target_ids]

    def is_positive(self, source_id: str, target_id: str) -> bool:
        """True if the two records are linked in the ground truth."""
        return (source_id, target_id) in self.links

    def split_candidates(self, source_id: str) -> tuple[list[str], list[str]]:
        """Returns a tuple of two lists: the first list contains the positive candidates (linked in ground truth),
        and the second list contains the negative candidates (not linked in ground truth) for the given source_id."""
        positive_candidates = []
        negative_candidates = []
        for target_id in self.candidates.get(source_id, []):
            if self.is_positive(source_id, target_id):
                positive_candidates.append(target_id)
            else:
                negative_candidates.append(target_id)
        return positive_candidates, negative_candidates
