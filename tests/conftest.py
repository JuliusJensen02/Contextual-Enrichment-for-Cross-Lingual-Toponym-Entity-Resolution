"""Shared setup for the tests.

Run from the repo root:  python -m pytest

The code in candidate_generation/ imports its own packages as top-level modules (`from base
import ...`, `from methods import ...`), so both the repo root and candidate_generation/ go
on sys.path here.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "candidate_generation"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from data_loader import Dataset, DatasetName  # noqa: E402

COLUMNS = ["id", "title", "title_ipa", "name_variants", "lat", "lon"]


def make_dataset(name: DatasetName, rows: list[dict]) -> Dataset:
    """A Dataset from a few rows; columns that are left out are empty strings."""
    frame = pd.DataFrame([{column: "" for column in COLUMNS} | row for row in rows], dtype=str)
    return Dataset(name, frame)


@pytest.fixture
def dataset_factory():
    return make_dataset
