"""Shared by the experiment scripts: paths, the test sets, the cached geo filter and embeddings."""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CANDIDATE_GENERATION = HERE.parent
ROOT = CANDIDATE_GENERATION.parent
for path in (ROOT, CANDIDATE_GENERATION):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from data_loader import DatasetName, TestSet, TestSetLoader, TestSetName  # noqa: E402

RERUN = CANDIDATE_GENERATION / "results" / "rerun"   # everything the experiments write
CACHE = RERUN / "cache"                              # embeddings and geo masks, not committed

TESTSETS = {"mehdie": TestSetName.MEHDIE, "pleiades-tm": TestSetName.PLEIADES_TRISMEGISTOS,
            "zh-ru": TestSetName.WIKIDATA_ZH_RU}
LABELS = {"mehdie": "MEHDIE", "pleiades-tm": "Pleiades-TM", "zh-ru": "zh-ru"}
# Datasets the experiments leave out: MEHDIE is run on Kima-Yaqut only (al-Thurayya has 19 of its 114 links).
EXCLUDED = {"mehdie": (DatasetName.THURAYYA,)}

MAX_KM = 100
CHUNK = 1000  # source records handled at a time


def load(testset: str) -> TestSet:
    return TestSetLoader().load(TESTSETS[testset]).without(*EXCLUDED.get(testset, ()))


def embedding_path(testset: str, dataset) -> Path:
    return CACHE / f"{testset}_{dataset.name.name}_labse.npy"


def far_path(testset: str, source, target, max_km=MAX_KM) -> Path:
    return CACHE / f"{testset}_{source.name}-{target.name}_far{max_km:g}.npy"


def far_mask(testset: str, source, target, max_km=MAX_KM) -> np.ndarray:
    """[source records, target records], True where the two places are more than max_km apart
    (written by prepare.py). Pairs where a record has no coordinates are False: never ruled out."""
    return np.load(far_path(testset, source, target, max_km), mmap_mode="r")
