"""Shared record construction used by every adapter."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from candidate_generation.data.name_cleaning import uniq
from candidate_generation.data.phonetics import phonetic_forms
from candidate_generation.data.schema import Record

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


def read_rows(path: Path, delimiter: str) -> list[dict[str, str]]:
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def parse_float(value: str | None) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except ValueError:
        return None


def make_record(
    record_id: str,
    source: str,
    names: list[str],
    lat: float | None = None,
    lon: float | None = None,
    feature_type: str | None = None,
) -> Record:
    """Build a Record from ordered names. The first name is the primary one."""
    ordered = uniq(names)
    forms = [phonetic_forms(n) for n in ordered]
    primary_script = forms[0][0] if forms else "Zzzz"
    has_latin_name = any(f[0] == "Latn" for f in forms)
    return Record(
        record_id=record_id,
        source=source,
        name=ordered[0] if ordered else "",
        name_variants=tuple(ordered[1:]),
        script=primary_script,
        transliteration=tuple(f[3] for f in forms),
        ipa=tuple(f[1] for f in forms),
        lat=lat,
        lon=lon,
        feature_type=feature_type or None,
        ipa_source=forms[0][2] if forms and forms[0][1] else "none",
        transliteration_source=("dataset" if has_latin_name else "derived")
        if ordered
        else "none",
    )
