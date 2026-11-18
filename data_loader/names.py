"""Names for what the loader can load: the datasets and the test sets."""
from enum import Enum


class DatasetName(Enum):
    """One member per dataset. `folder` and `file` say where its minimized file is, inside
    datasets/02_minimized_datasets/. `label` is the dataset's name in tables and in the
    normalized ground truth (the source_dataset / target_dataset columns)."""

    KIMA = ("MEHDIE", "kima.tsv", "Kima")
    YAQUT = ("MEHDIE", "yaqut.tsv", "Yaqut")
    THURAYYA = ("MEHDIE", "thurayya.tsv", "Thurayya")

    PLEIADES = ("Pleades_Trismegistos", "pleiades.tsv", "Pleiades")              # the places with a Greek name
    TRISMEGISTOS = ("Pleades_Trismegistos", "trismegistos.tsv", "Trismegistos")  # the places with a Latin name

    WIKIDATA_ZH = ("Wikidata-zh-ru", "wikidata_zh.tsv", "Wikidata_zh")
    WIKIDATA_RU = ("Wikidata-zh-ru", "wikidata_ru.tsv", "Wikidata_ru")

    def __init__(self, folder, file, label):
        self.folder = folder
        self.file = file
        self.label = label


class TestSetName(Enum):
    """One member per test set: the datasets it holds and its ground truth file, inside datasets/em/."""

    __test__ = False  # not a pytest test class, despite the name

    MEHDIE = ((DatasetName.KIMA, DatasetName.YAQUT, DatasetName.THURAYYA), "MEHDIE/em_internal.csv")
    PLEIADES_TRISMEGISTOS = ((DatasetName.PLEIADES, DatasetName.TRISMEGISTOS), "Pleades_Trismegistos/em.tsv")
    WIKIDATA_ZH_RU = ((DatasetName.WIKIDATA_ZH, DatasetName.WIKIDATA_RU), "Wikidata-zh-ru/em.tsv")

    def __init__(self, datasets, ground_truth):
        self.datasets = datasets
        self.ground_truth = ground_truth
