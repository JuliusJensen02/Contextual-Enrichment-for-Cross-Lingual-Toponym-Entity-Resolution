"""Generator interface and the max-over-variants aggregation they share.

A generator returns a dense score matrix for a chunk of queries against all targets.
NaN means "not retrieved". Working on full matrices is what makes recall exact: every
query-target pair of the cross product gets a score, and nothing is estimated.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

import numpy as np

from candidate_generation.data.schema import NameTable, assert_name_only


class StringGroups:
    """Per-record strings flattened so each record owns a contiguous slice."""

    def __init__(self, groups: tuple[tuple[str, ...], ...]):
        self.flat: list[str] = []
        offsets = [0]
        has_string = []
        for group in groups:
            strings = list(dict.fromkeys(s for s in group if s))
            has_string.append(bool(strings))
            # Every record keeps one slot, so reduceat never meets an empty slice.
            self.flat.extend(strings or [""])
            offsets.append(len(self.flat))
        self.offsets = np.asarray(offsets, dtype=np.int64)
        self.has_string = np.asarray(has_string, dtype=bool)

    def __len__(self) -> int:
        return len(self.offsets) - 1

    def chunk(self, indices: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Return the flat positions of `indices` and their group start offsets."""
        starts = self.offsets[indices]
        stops = self.offsets[indices + 1]
        positions = np.concatenate([np.arange(a, b) for a, b in zip(starts, stops)])
        chunk_offsets = np.concatenate([[0], np.cumsum(stops - starts)[:-1]])
        return positions, chunk_offsets


def group_max(
    matrix: np.ndarray, row_offsets: np.ndarray, column_offsets: np.ndarray
) -> np.ndarray:
    """Collapse a string-by-string matrix to record-by-record by taking the maximum."""
    collapsed = np.maximum.reduceat(matrix, row_offsets, axis=0)
    return np.maximum.reduceat(collapsed, column_offsets, axis=1)


class Generator(ABC):
    """A candidate generator. Subclasses declare the fields they read."""

    name: ClassVar[str]
    input_fields: ClassVar[frozenset[str]]

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        assert_name_only(cls.input_fields)

    def prepare(self, query: NameTable, target: NameTable) -> None:
        """Index one query/target table pair."""
        if not isinstance(query, NameTable) or not isinstance(target, NameTable):
            raise TypeError(
                "generators only accept NameTable inputs, never raw records"
            )
        assert_name_only(self.input_fields)
        self._prepare(query, target)

    @abstractmethod
    def _prepare(self, query: NameTable, target: NameTable) -> None: ...

    @abstractmethod
    def score(self, query_indices: np.ndarray) -> np.ndarray:
        """Return a float32 (n_queries, n_targets) matrix, NaN where not retrieved."""

    def metadata(self) -> dict:
        return {"name": self.name, "fields": sorted(self.input_fields)}
