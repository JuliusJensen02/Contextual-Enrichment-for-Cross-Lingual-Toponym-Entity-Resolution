from pathlib import Path

import pandas as pd

from .dataset import Dataset
from .ground_truth import GroundTruth
from .names import DatasetName, TestSetName
from .testset import TestSet

DATASETS_DIR = Path(__file__).resolve().parents[1] / "datasets"


class TestSetLoader:
    """Loads a test set by enum: its minimized datasets plus its (normalized) ground truth.

        mehdie = TestSetLoader().load(TestSetName.MEHDIE)     # a TestSet
        mehdie.datasets                                       # [Dataset(KIMA, ...), ...]
        mehdie.ground_truth                                   # GroundTruth

    Datasets come from datasets/02_minimized_datasets/, ground truth from datasets/em/. All
    tables hold strings only; empty cells are "" (never NaN), so ids keep their leading zeros
    and multi-value cells ("a | b") stay as written.
    """

    __test__ = False  # not a pytest test class, despite the name

    def __init__(self, root: Path = DATASETS_DIR):
        self.root = Path(root)

    def load(self, name: TestSetName) -> TestSet:
        datasets = [self._load_dataset(dataset_name) for dataset_name in name.datasets]
        return TestSet(name, datasets, self._load_ground_truth(name))

    def _load_dataset(self, name: DatasetName) -> Dataset:
        return Dataset(name, self._read(self.root / "02_minimized_datasets" / name.folder / name.file))

    def _load_ground_truth(self, name: TestSetName) -> GroundTruth:
        return GroundTruth(name, self._read(self.root / "em" / name.ground_truth))

    @staticmethod
    def _read(path: Path) -> pd.DataFrame:
        sep = "," if path.suffix == ".csv" else "\t"
        return pd.read_csv(path, sep=sep, dtype=str, keep_default_na=False)
