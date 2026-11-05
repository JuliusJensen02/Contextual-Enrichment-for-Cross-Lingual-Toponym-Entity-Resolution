"""The common record schema, and the name-only view generators are allowed to see.

`Record` carries everything an adapter knows, including coordinates and feature
type. Those two exist for the later LLM attribute ablation. Generators must never
see them, so a generator only ever receives a `NameTable`, which is built from the
name-derived fields alone. `assert_name_only` is the enforcement point.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

# The only fields a candidate generator may read.
NAME_FIELDS = frozenset({"name", "name_variants", "transliteration", "ipa"})
# Attributes ablated in the LLM prompts. Using them for blocking would confound that.
FORBIDDEN_FIELDS = frozenset({"lat", "lon", "feature_type"})


def assert_name_only(fields: Iterable[str]) -> None:
    """Fail if a generator declares any field outside the name-derived set."""
    declared = set(fields)
    forbidden = declared & FORBIDDEN_FIELDS
    assert not forbidden, (
        f"generators must not use attribute fields: {sorted(forbidden)}"
    )
    unknown = declared - NAME_FIELDS
    assert not unknown, (
        f"generators may only use name-derived fields, got: {sorted(unknown)}"
    )


@dataclass(frozen=True)
class Record:
    """One place, normalised.

    `name` is the primary name; `name_variants` holds the other forms. `ipa` and
    `transliteration` are aligned with `all_names`, so element 0 belongs to `name`.
    An empty string means no form could be derived for that name. `ipa_source` and
    `transliteration_source` are provenance for the coverage report.
    """

    record_id: str
    source: str
    name: str
    name_variants: tuple[str, ...]
    script: str
    transliteration: tuple[str, ...]
    ipa: tuple[str, ...]
    lat: float | None = None
    lon: float | None = None
    feature_type: str | None = None
    ipa_source: str = "none"
    transliteration_source: str = "none"

    @property
    def all_names(self) -> tuple[str, ...]:
        return ((self.name,) if self.name else ()) + self.name_variants


@dataclass(frozen=True)
class Task:
    """One ordered gazetteer pair. `pairs` are (source_id, target_id), the ground truth."""

    name: str
    source: str
    target: str
    pairs: tuple[tuple[str, str], ...]


@dataclass
class Dataset:
    name: str
    gazetteers: dict[str, list[Record]]
    tasks: list[Task]
    directions: list[str]
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class NameTable:
    """Name-derived fields for a list of records, and nothing else."""

    record_ids: tuple[str, ...]
    names: tuple[tuple[str, ...], ...]
    transliteration: tuple[tuple[str, ...], ...]
    ipa: tuple[tuple[str, ...], ...]

    def __len__(self) -> int:
        return len(self.record_ids)

    def representation(self, kind: str) -> tuple[tuple[str, ...], ...]:
        """Return the per-record string lists for 'ipa', 'transliteration' or 'name'."""
        if kind == "name":
            return self.names
        if kind in ("ipa", "transliteration"):
            return getattr(self, kind)
        raise ValueError(f"unknown representation: {kind}")


def name_table(records: Iterable[Record | Mapping]) -> NameTable:
    """Project records onto the name-derived fields."""
    rows = list(records)
    return NameTable(
        record_ids=tuple(r.record_id for r in rows),
        names=tuple(r.all_names for r in rows),
        transliteration=tuple(r.transliteration for r in rows),
        ipa=tuple(r.ipa for r in rows),
    )


def records_by_id(records: Iterable[Record]) -> dict[str, Record]:
    return {r.record_id: r for r in records}
