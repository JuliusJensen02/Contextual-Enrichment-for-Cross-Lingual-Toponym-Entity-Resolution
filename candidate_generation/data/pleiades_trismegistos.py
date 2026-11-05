"""Adapter for final_datasets/Pleades_Trismegistos."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from candidate_generation.data.build import make_record, parse_float, read_rows
from candidate_generation.data.name_cleaning import (
    PLACEHOLDER,
    clean_egyptian_name,
    clean_pleiades_name,
    clean_tm_name,
    split_multi,
    uniq,
)
from candidate_generation.data.schema import Dataset, Record, Task


def _pleiades_names(row: dict[str, str]) -> list[str]:
    names = clean_pleiades_name(row["title"])
    for column in ("names_romanized", "names_latin", "names_greek"):
        for raw in split_multi(row.get(column, "")):
            names.extend(clean_pleiades_name(raw))
    for tagged in split_multi(row.get("names_by_language", "")):
        names.extend(clean_pleiades_name(tagged.rsplit("@", 1)[0]))
    return uniq(names)


def load_pleiades(path: Path) -> tuple[list[Record], dict[str, int]]:
    rows = read_rows(path / "pleiades.tsv", "\t")
    records = []
    stats = Counter()
    for row in rows:
        stats["placeholder_titles"] += bool(PLACEHOLDER.search(row["title"]))
        stats["titles_with_parentheses"] += "(" in row["title"]
        names = _pleiades_names(row)
        stats["no_usable_name"] += not names
        records.append(
            make_record(
                row["pleiades_id"],
                "pleiades",
                names,
                parse_float(row.get("lat")),
                parse_float(row.get("lon")),
                row.get("place_types"),
            )
        )
    return records, dict(stats)


def _tm_names(row: dict[str, str]) -> list[str]:
    names = clean_tm_name(row["name_standard"])
    for column in ("names_latin", "names_greek", "names_coptic", "modern_name"):
        for raw in split_multi(row.get(column, "")):
            names.extend(clean_tm_name(raw))
    for raw in split_multi(row.get("names_egyptian", "")):
        names.extend(clean_egyptian_name(raw))
    return uniq(names)


def load_trismegistos(path: Path) -> tuple[list[Record], dict[str, int]]:
    rows = read_rows(path / "trismegistos.tsv", "\t")
    records = []
    stats = Counter()
    for row in rows:
        stats["lacunose_standard_names"] += (
            "[" in row["name_standard"] or "( )" in row["name_standard"]
        )
        names = _tm_names(row)
        stats["no_usable_name"] += not names
        records.append(
            make_record(
                row["trismegistos_id"],
                "trismegistos",
                names,
                parse_float(row.get("lat")),
                parse_float(row.get("lon")),
                row.get("status"),
            )
        )
    return records, dict(stats)


def load_pleiades_trismegistos(config: dict, root: Path) -> Dataset:
    path = root / config["path"]
    pleiades, pleiades_stats = load_pleiades(path)
    trismegistos, tm_stats = load_trismegistos(path)
    rows = read_rows(path / "em.tsv", "\t")
    pairs = tuple(sorted({(r["pleiades_id"], r["trismegistos_id"]) for r in rows}))
    task = config["tasks"][0]
    return Dataset(
        name="pleiades_trismegistos",
        gazetteers={"pleiades": pleiades, "trismegistos": trismegistos},
        tasks=[Task(task["name"], task["source"], task["target"], pairs)],
        directions=config["directions"],
        notes={
            "pleiades": pleiades_stats,
            "trismegistos": tm_stats,
            "ground_truth_rows": len(rows),
        },
    )
