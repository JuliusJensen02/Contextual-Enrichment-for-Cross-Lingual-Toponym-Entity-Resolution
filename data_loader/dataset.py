import re
from functools import cached_property

import pandas as pd

from .names import DatasetName

PIPE = r"\s*\|\s*"            # "a | b"
VARIANTS = r"\s*[|;،]\s*"     # name variants are also packed with ";" and with the Arabic comma


class Dataset:
    """One loaded (minimized) dataset: its table (`frame`) plus the same operations for every
    dataset, so code that uses a dataset does not need to know its columns or separators.

        kima = TestSetLoader().load(TestSetName.MEHDIE).dataset(DatasetName.KIMA)
        len(kima), kima.ids                 # the records
        kima.names["138113"]                # ["ג'דידה", "Jadida", ...]  main name first
        kima.phonetic["138113"]             # ["dʒdida"]
        kima.coordinates["138113"]          # [(lat, lon), ...]  can be empty or several
        kima.filter(kima.frame.lat != "")   # a new Dataset with only those rows
        kima.subset(["138113", "138114"])   # a new Dataset with those records, in that order

    `frame` is the table as loaded: strings only, "" for empty cells. Every dataset has the
    columns id, title, title_ipa, name_variants, lat, lon; the rest differ (see minimized_README.md).
    """

    def __init__(self, name: DatasetName, frame: pd.DataFrame):
        self.name = name
        self.frame = frame

    def __len__(self) -> int:
        return len(self.frame)

    def __contains__(self, record_id) -> bool:
        return record_id in self._positions

    def __repr__(self) -> str:
        return f"Dataset({self.name.name}, {len(self)} records)"

    @property
    def label(self) -> str:
        """The dataset's name in tables and logs, e.g. "Kima" (DatasetName.label)."""
        return self.name.label

    # ------------------------------------------------------------------ records
    @cached_property
    def ids(self) -> list[str]:
        """The record ids, in row order. The ground truth links refer to these."""
        return list(self.frame["id"])

    @cached_property
    def names(self) -> dict[str, list[str]]:
        """{record_id: its names}, main name first, without duplicates or blanks: the title,
        the name variants and, where the dataset has one, the Wikipedia title. A trailing
        qualifier ("Aethusa (island)") and language tags ("Ἄλπεις@grc") are removed."""
        columns = [self.frame["title"], self.frame["name_variants"]]
        if "wiki_title" in self.frame:
            columns.append(self.frame["wiki_title"])
        return {rid: _distinct(_clean(name) for cell in cells for name in re.split(VARIANTS, cell))
                for rid, *cells in zip(self.ids, *columns)}

    @cached_property
    def phonetic(self) -> dict[str, list[str]]:
        """{record_id: the IPA encodings of its main name} (one, or several for Trismegistos)."""
        return {rid: _distinct(ipa.strip() for ipa in re.split(PIPE, cell))
                for rid, cell in zip(self.ids, self.frame["title_ipa"])}

    @cached_property
    def coordinates(self) -> dict[str, list[tuple[float, float]]]:
        """{record_id: its (lat, lon) points}: none, one or several."""
        return {rid: [(float(a), float(b)) for a, b in zip(re.split(r"[;|]", lat), re.split(r"[;|]", lon))
                      if a.strip() and b.strip()]
                for rid, lat, lon in zip(self.ids, self.frame["lat"], self.frame["lon"])}

    # ------------------------------------------------------------------ making smaller datasets
    def filter(self, mask) -> "Dataset":
        """The rows where `mask` (a boolean Series over `frame`) is True, as a new Dataset."""
        return Dataset(self.name, self.frame[mask])

    def subset(self, record_ids) -> "Dataset":
        """The given records, in the given order, as a new Dataset."""
        return Dataset(self.name, self.frame.iloc[[self._positions[rid] for rid in record_ids]])

    # ------------------------------------------------------------------ helpers
    @cached_property
    def _positions(self) -> dict[str, int]:
        return {rid: i for i, rid in enumerate(self.ids)}


def _clean(name: str) -> str:
    name = re.sub(r"@[A-Za-z-]+$", "", name.strip())      # language tag
    return re.sub(r"\s+\([^)]*\)$", "", name).strip()     # trailing qualifier


def _distinct(values) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))
