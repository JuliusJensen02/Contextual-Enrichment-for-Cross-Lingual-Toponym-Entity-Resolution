import json
from pathlib import Path

import pandas as pd

from .candidates import CandidateSet, candidates_path
from .dataset import Dataset
from .ground_truth import read_links
from .names import TestSetName
from .record import Record
from .testset import TestSet

DATASETS_DIR = Path(__file__).resolve().parents[1] / "datasets"


class TestSetLoader:
    """Loads a test set: its minimized datasets (datasets/02_minimized_datasets/), its ground
    truth (datasets/em/) and its stored candidates (datasets/03_candidate_generation/).

        mehdie = TestSetLoader().load(TestSetName.MEHDIE)     # a TestSet
        TestSetLoader().load_candidates(TestSetName.MEHDIE)   # one CandidateSet per pair of datasets

    Every cell is read as a string and empty cells stay "" (never NaN), so ids keep their
    leading zeros.
    """

    __test__ = False  # not a pytest test class, despite the name

    def __init__(self, root: Path = DATASETS_DIR):
        self.root = Path(root)

    def load(self, name: TestSetName) -> TestSet:
        datasets = []
        for dataset_name in name.datasets:
            rows = _read(self.root / "02_minimized_datasets" / dataset_name.folder / dataset_name.file)
            datasets.append(Dataset(dataset_name, (Record.from_row(dataset_name, row) for row in rows)))
        links = read_links(name, _read(self.root / "em" / name.ground_truth))
        return TestSet(name, datasets, links)

    def load_candidates(self, name: TestSetName) -> list[CandidateSet]:
        test_set = self.load(name)
        candidate_sets = []
        for source, target in test_set.pairs:
            stored = json.loads(candidates_path(self.root, source, target).read_text(encoding="utf8"))
            candidate_sets.append(CandidateSet(test_set.dataset(source), test_set.dataset(target),
                                               stored["candidates"], test_set.links_between(source, target)))
        return candidate_sets


def _read(path: Path) -> list[dict[str, str]]:
    """The rows of a .csv or .tsv file."""
    frame = pd.read_csv(path, sep="," if path.suffix == ".csv" else "\t", dtype=str, keep_default_na=False)
    return frame.to_dict("records")
