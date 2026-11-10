#!/usr/bin/env python3
"""Build Greek Pleiades and Latin Trismegistos inputs plus filtered gold links.

Trismegistos text rows are aggregated to one row per place. Text fields with
multiple distinct values are joined with `` | ``; ``mentions_name`` is 1 if
any linked text mentions the place name.

Usage: python scripts/build_greek_latin_crosslingual.py
       [--pleiades PATH] [--trismegistos PATH] [--em PATH] [--output-dir DIR]
"""

from __future__ import annotations

import argparse
import csv
import tempfile
from pathlib import Path

from load_trismegistos_partitions import load_partitions

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "final_datasets" / "Pleades_Trismegistos"
OUTPUT_DIR = DATA_DIR / "pleiades_greek_trismegistos_latin"

PLEIADES_ID = "pleiades_id"
TRISMEGISTOS_ID = "trismegistos_id"
SEPARATOR = " | "
TEXT_COLUMNS = (
    "tm_text_id",
    "relation",
    "title",
    "material",
    "text_lang",
    "year_from",
    "year_to",
    "keywords",
    "mentions_name",
    "snippet",
    "edition_text",
    "translation_en",
)

csv.field_size_limit(10**9)


def require_columns(path: Path, fields: list[str] | None, required: tuple[str, ...]) -> list[str]:
    if not fields:
        raise ValueError(f"{path} has no header row")
    missing = [field for field in required if field not in fields]
    if missing:
        raise ValueError(f"{path} is missing required columns: {', '.join(missing)}")
    return fields


def build_pleiades(source: Path, output: Path) -> set[str]:
    ids = set()
    with source.open(encoding="utf-8", newline="") as source_file:
        reader = csv.DictReader(source_file, delimiter="\t")
        fields = require_columns(source, reader.fieldnames, (PLEIADES_ID, "names_greek"))
        with output.open("w", encoding="utf-8", newline="") as output_file:
            writer = csv.DictWriter(output_file, fieldnames=fields, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            for row in reader:
                place_id = row[PLEIADES_ID]
                if not place_id:
                    raise ValueError(f"{source} contains a row with an empty {PLEIADES_ID}")
                if not row["names_greek"].strip():
                    continue
                if place_id in ids:
                    raise ValueError(f"{source} contains duplicate {PLEIADES_ID} {place_id!r}")
                ids.add(place_id)
                writer.writerow(row)
    return ids


def write_trismegistos_group(
    writer: csv.DictWriter,
    place: dict[str, str] | None,
    values: dict[str, list[str]],
    mentions_name: bool,
) -> bool:
    if place is None or not place["names_latin"].strip():
        return False
    row = dict(place)
    for field in TEXT_COLUMNS:
        row[field] = (
            ("1" if mentions_name else "0")
            if field == "mentions_name"
            else SEPARATOR.join(values[field])
        )
    writer.writerow(row)
    return True


def build_trismegistos(source: Path, output: Path) -> set[str]:
    ids = set()
    text_ids = set(TEXT_COLUMNS)
    with source.open(encoding="utf-8", newline="") as source_file:
        reader = csv.DictReader(source_file, delimiter="\t")
        fields = require_columns(
            source,
            reader.fieldnames,
            (TRISMEGISTOS_ID, "names_latin", *TEXT_COLUMNS),
        )
        place_fields = [field for field in fields if field not in text_ids]
        with output.open("w", encoding="utf-8", newline="") as output_file:
            writer = csv.DictWriter(output_file, fieldnames=fields, delimiter="\t", lineterminator="\n")
            writer.writeheader()

            current_id = None
            place = None
            values = {field: [] for field in TEXT_COLUMNS if field != "mentions_name"}
            seen_values = {field: set() for field in values}
            mentions_name = False
            closed_ids = set()

            def flush_group() -> None:
                if write_trismegistos_group(writer, place, values, mentions_name) and current_id is not None:
                    ids.add(current_id)

            for row in reader:
                place_id = row[TRISMEGISTOS_ID]
                if not place_id:
                    raise ValueError(f"{source} contains a row with an empty {TRISMEGISTOS_ID}")

                if place_id != current_id:
                    flush_group()
                    if place_id in closed_ids:
                        raise ValueError(
                            f"{source} has non-contiguous rows for {TRISMEGISTOS_ID} {place_id!r}"
                        )
                    if current_id is not None:
                        closed_ids.add(current_id)
                    current_id = place_id
                    place = {field: row[field] for field in place_fields}
                    values = {field: [] for field in TEXT_COLUMNS if field != "mentions_name"}
                    seen_values = {field: set() for field in values}
                    mentions_name = False
                elif any(row[field] != place[field] for field in place_fields):
                    raise ValueError(
                        f"{source} has inconsistent place attributes for {TRISMEGISTOS_ID} {place_id!r}"
                    )

                if row["mentions_name"].strip() == "1":
                    mentions_name = True
                for field in values:
                    value = row[field]
                    if value and value not in seen_values[field]:
                        seen_values[field].add(value)
                        values[field].append(value)

            flush_group()
    return ids


def build_em(source: Path, output: Path, pleiades_ids: set[str], trismegistos_ids: set[str]) -> int:
    with source.open(encoding="utf-8", newline="") as source_file:
        reader = csv.DictReader(source_file, delimiter="\t")
        fields = require_columns(source, reader.fieldnames, (PLEIADES_ID, TRISMEGISTOS_ID))
        count = 0
        with output.open("w", encoding="utf-8", newline="") as output_file:
            writer = csv.DictWriter(output_file, fieldnames=fields, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            for row in reader:
                if row[PLEIADES_ID] in pleiades_ids and row[TRISMEGISTOS_ID] in trismegistos_ids:
                    writer.writerow(row)
                    count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pleiades", type=Path, default=DATA_DIR / "pleiades.tsv")
    parser.add_argument(
        "--trismegistos",
        type=Path,
        default=DATA_DIR / "trismegistos_texts_combined_parts",
        help="Partition directory from combine_trismegistos.py, or a combined TSV file",
    )
    parser.add_argument("--em", type=Path, default=DATA_DIR / "em.tsv")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()

    input_paths = {path.resolve() for path in (args.pleiades, args.trismegistos, args.em)}
    output_paths = {
        (args.output_dir / name).resolve()
        for name in ("pleiades.tsv", "trismegistos.tsv", "em.tsv")
    }
    if input_paths.intersection(output_paths):
        raise ValueError("Output files must not overwrite any input file")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="trismegistos-partitions-") as temp_dir:
        if args.trismegistos.is_dir():
            combined_path = Path(temp_dir) / "trismegistos_texts_combined.tsv"
            row_count, partition_count = load_partitions(args.trismegistos, combined_path)
            print(f"Loaded {row_count:,} rows from {partition_count:,} Trismegistos partitions")
        else:
            combined_path = args.trismegistos

        pleiades_ids = build_pleiades(args.pleiades, args.output_dir / "pleiades.tsv")
        trismegistos_ids = build_trismegistos(
            combined_path,
            args.output_dir / "trismegistos.tsv",
        )
        em_count = build_em(
            args.em,
            args.output_dir / "em.tsv",
            pleiades_ids,
            trismegistos_ids,
        )

    print(f"Pleiades Greek: {len(pleiades_ids):,} places")
    print(f"Trismegistos Latin: {len(trismegistos_ids):,} places")
    print(f"Gold links: {em_count:,} pairs")
    print(f"Output directory: {args.output_dir}")


if __name__ == "__main__":
    main()
