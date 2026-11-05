"""Adapter for final_datasets/MEHDIE.

The extract repeats places: Kima has 14,341 rows for 6,211 src_ids, and al-Thurayya
has every place twice. The ground truth points at one arbitrary row, so a generator
retrieving the other copy would be scored as a miss. Records are therefore collapsed
to one place per src_id, merging names, and link endpoints are mapped to places. The
record_id is the src_id. The `links` column is never read, because it leaks matches.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from candidate_generation.data.build import make_record, read_rows
from candidate_generation.data.name_cleaning import split_variants, tidy, uniq
from candidate_generation.data.phonetics import detect_script
from candidate_generation.data.schema import Dataset, Record, Task

FILES = {
    "kima": "mehdie_db_kima_extract.csv",
    "yaqut": "mehdie_db_yaqut_extract.csv",
    "thurayya": "mehdie_db_thurayya_extract.csv",
}
# The script a gazetteer's primary name should be in, when any copy has one.
PREFERRED_SCRIPT = {"kima": "Hebr", "yaqut": "Arab", "thurayya": "Arab"}
# al-Thurayya packs several names into one toponym, separated by ':' and the Arabic comma.
VARIANT_SEPARATORS = ":،"


def _json(value: str):
    try:
        return json.loads(value) if value else []
    except json.JSONDecodeError:
        return []


def _row_names(row: dict[str, str]) -> list[str]:
    names = [tidy(row["title"])]
    for entry in _json(row["names"]):
        names.extend(split_variants(entry.get("toponym", ""), VARIANT_SEPARATORS))
    return uniq(names)


def _first_point(row: dict[str, str]) -> tuple[float | None, float | None]:
    for geometry in _json(row["geoms"]):
        coordinates = geometry.get("coordinates")
        if isinstance(coordinates, list) and len(coordinates) == 2:
            return float(coordinates[1]), float(coordinates[0])
    return None, None


def _feature_type(row: dict[str, str], source: str) -> str | None:
    if source == "thurayya":
        descriptions = _json(row["descriptions"])
        return descriptions[0].get("value") if descriptions else None
    labels = [t.get("label") or t.get("sourceLabel") for t in _json(row["types"])]
    return next((label for label in labels if label), None)


def _collapse(
    rows: list[dict[str, str]], source: str
) -> tuple[list[Record], dict[str, str]]:
    """Merge rows sharing a src_id. Returns the records and a row id -> place id map."""
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in sorted(rows, key=lambda r: int(r["id"])):
        groups[row["src_id"]].append(row)
    records = []
    place_of_row: dict[str, str] = {}
    for src_id, group in groups.items():
        names = uniq(name for row in group for name in _row_names(row))
        preferred = PREFERRED_SCRIPT[source]
        names.sort(key=lambda n: detect_script(n) != preferred)
        lat, lon = next(
            (p for p in map(_first_point, group) if p[0] is not None), (None, None)
        )
        feature = next(
            (f for f in (_feature_type(r, source) for r in group) if f), None
        )
        records.append(make_record(src_id, source, names, lat, lon, feature))
        place_of_row.update({row["id"]: src_id for row in group})
    return records, place_of_row


def load_mehdie(config: dict, root: Path) -> Dataset:
    path = root / config["path"]
    gazetteers: dict[str, list[Record]] = {}
    place_of_row: dict[str, tuple[str, str]] = {}
    rows_per_source: dict[str, int] = {}
    for source, filename in FILES.items():
        rows = read_rows(path / filename, ",")
        rows_per_source[source] = len(rows)
        records, mapping = _collapse(rows, source)
        gazetteers[source] = records
        place_of_row.update({row: (source, place) for row, place in mapping.items()})

    positive: set[frozenset] = set()
    negative: set[frozenset] = set()
    link_types = Counter()
    for link in read_rows(path / "internal_links_kima_yaqut_thurayya.csv", ","):
        link_types[link["link_type"]] += 1
        ends = frozenset(
            (
                place_of_row[link["source_place_id"]],
                place_of_row[link["target_place_id"]],
            )
        )
        if link["link_type"] == "same_as":
            positive.add(ends)
        elif link["link_type"] == "different":
            negative.add(ends)

    conflicts = positive & negative
    if config.get("conflict_policy", "exclude") == "exclude":
        ground_truth = positive - conflicts
    else:
        ground_truth = positive

    tasks = []
    for task in config["tasks"]:
        pairs = set()
        for ends in ground_truth:
            by_source = dict(ends)
            if task["source"] in by_source and task["target"] in by_source:
                pairs.add((by_source[task["source"]], by_source[task["target"]]))
        tasks.append(
            Task(task["name"], task["source"], task["target"], tuple(sorted(pairs)))
        )

    return Dataset(
        name="mehdie",
        gazetteers=gazetteers,
        tasks=tasks,
        directions=config["directions"],
        notes={
            "rows_per_source": rows_per_source,
            "places_per_source": {s: len(r) for s, r in gazetteers.items()},
            "link_types": dict(link_types),
            "same_as_place_pairs": len(positive),
            "conflicting_pairs_excluded": sorted(
                sorted(map(str, ends)) for ends in conflicts
            ),
        },
    )
